"""
Firebase listener manager.
Supports:
  - public        → REST polling (only database URL)
  - private_sa    → firebase-admin Service Account
  - private_secret→ REST polling with ?auth=SECRET
"""
import json
import logging
import threading
import time
from typing import Dict, Optional, Callable, List

import requests
import firebase_admin
from firebase_admin import credentials, db, delete_app

from models import FirebaseAccount, User

logger = logging.getLogger(__name__)

POLL_INTERVAL = 4  # seconds for public / secret polling


class FirebaseManager:
    def __init__(self):
        self._apps: Dict[int, firebase_admin.App] = {}       # telegram_id → app (SA only)
        self._listeners: Dict[int, list] = {}                # telegram_id → registrations / threads
        self._stop_flags: Dict[int, threading.Event] = {}
        self._seen: Dict[int, set] = {}                      # telegram_id → set of seen sms keys
        self._lock = threading.Lock()
        self._on_sms: Optional[Callable] = None

    def set_callback(self, callback: Callable):
        self._on_sms = callback

    # ── helpers ──────────────────────────────────────────────
    def _get_active_fb(self, user: User, session) -> Optional[FirebaseAccount]:
        if not user.active_firebase_id:
            return None
        return (
            session.query(FirebaseAccount)
            .filter(
                FirebaseAccount.id == user.active_firebase_id,
                FirebaseAccount.user_id == user.id,
            )
            .first()
        )

    def _normalize_url(self, url: str) -> str:
        url = url.strip().rstrip("/")
        if not url.endswith(".json"):
            # keep as base URL
            pass
        return url

    # ── start / stop ─────────────────────────────────────────
    def start_listening(self, user: User, session) -> bool:
        callback = self._on_sms
        if not callback:
            logger.error("No SMS callback set")
            return False

        fb = self._get_active_fb(user, session)
        if not fb:
            logger.error("No active Firebase selected")
            return False
        if not user.selected_devices:
            logger.error("No devices selected")
            return False

        with self._lock:
            self._stop_listening_unlocked(user.telegram_id)
            self._seen[user.telegram_id] = set()
            self._listeners[user.telegram_id] = []
            stop_event = threading.Event()
            self._stop_flags[user.telegram_id] = stop_event

            devices = list(user.selected_devices or [])

            if fb.fb_type == "private_sa":
                ok = self._start_sa_listeners(user, fb, devices, callback, stop_event)
            else:
                # public or private_secret → REST polling
                ok = self._start_poll_listeners(user, fb, devices, callback, stop_event)

            return ok

    def _start_sa_listeners(self, user, fb, devices, callback, stop_event) -> bool:
        try:
            name = f"user_{user.telegram_id}"
            try:
                old = firebase_admin.get_app(name)
                delete_app(old)
            except ValueError:
                pass

            sa_dict = json.loads(fb.credentials)
            cred = credentials.Certificate(sa_dict)
            app = firebase_admin.initialize_app(
                cred, {"databaseURL": fb.database_url}, name=name
            )
            self._apps[user.telegram_id] = app

            for device_id in devices:
                ref = db.reference(f"devices/{device_id}/sms", app=app)

                def make_cb(dev_id, tid, fb_name):
                    def _cb(event):
                        if stop_event.is_set():
                            return
                        if event.event_type in ("put", "patch") and event.data is not None:
                            try:
                                callback(tid, dev_id, event.data, event.path, fb_name)
                            except Exception as e:
                                logger.error(f"SA callback error: {e}")
                    return _cb

                reg = ref.listen(make_cb(device_id, user.telegram_id, fb.name))
                self._listeners[user.telegram_id].append(reg)
                logger.info(f"SA listener started: user={user.telegram_id} device={device_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to start SA listeners: {e}", exc_info=True)
            return False

    def _start_poll_listeners(self, user, fb, devices, callback, stop_event) -> bool:
        base = self._normalize_url(fb.database_url)
        auth_param = ""
        if fb.fb_type == "private_secret" and fb.credentials:
            auth_param = f"?auth={fb.credentials}"

        def poll_loop():
            tid = user.telegram_id
            fb_name = fb.name
            while not stop_event.is_set():
                for device_id in devices:
                    if stop_event.is_set():
                        break
                    try:
                        url = f"{base}/devices/{device_id}/sms.json{auth_param}"
                        r = requests.get(url, timeout=15)
                        if r.status_code != 200:
                            logger.warning(f"Poll {url} → {r.status_code}")
                            continue
                        data = r.json()
                        if not isinstance(data, dict):
                            continue
                        seen = self._seen.setdefault(tid, set())
                        for sms_id, sms in data.items():
                            key = f"{device_id}:{sms_id}"
                            if key in seen:
                                continue
                            seen.add(key)
                            # keep set from growing forever
                            if len(seen) > 5000:
                                self._seen[tid] = set(list(seen)[-2000:])
                            if isinstance(sms, dict):
                                try:
                                    callback(tid, device_id, sms, sms_id, fb_name)
                                except Exception as e:
                                    logger.error(f"Poll callback error: {e}")
                    except Exception as e:
                        logger.error(f"Poll error device={device_id}: {e}")
                stop_event.wait(POLL_INTERVAL)

        t = threading.Thread(target=poll_loop, daemon=True, name=f"poll-{user.telegram_id}")
        t.start()
        self._listeners[user.telegram_id].append(t)
        logger.info(f"Poll listeners started for user {user.telegram_id} ({fb.fb_type})")
        return True

    def _stop_listening_unlocked(self, telegram_id: int):
        # signal poll threads
        flag = self._stop_flags.pop(telegram_id, None)
        if flag:
            flag.set()

        listeners = self._listeners.pop(telegram_id, [])
        for item in listeners:
            try:
                if hasattr(item, "close"):  # firebase ListenerRegistration
                    item.close()
                # threads will exit via stop flag
            except Exception:
                pass

        app = self._apps.pop(telegram_id, None)
        if app:
            try:
                delete_app(app)
            except Exception:
                pass
        self._seen.pop(telegram_id, None)

    def stop_listening(self, telegram_id: int):
        with self._lock:
            self._stop_listening_unlocked(telegram_id)
            logger.info(f"Stopped listeners for {telegram_id}")

    def stop_all(self):
        with self._lock:
            for tid in list(self._apps.keys()) + list(self._listeners.keys()):
                self._stop_listening_unlocked(tid)
            logger.info("All listeners stopped")

    def is_listening(self, telegram_id: int) -> bool:
        return telegram_id in self._listeners and len(self._listeners[telegram_id]) > 0

    def list_devices(self, fb: FirebaseAccount) -> List[str]:
        """Return device IDs under /devices."""
        try:
            if fb.fb_type == "private_sa":
                name = f"tmp_{id(fb)}"
                try:
                    old = firebase_admin.get_app(name)
                    delete_app(old)
                except ValueError:
                    pass
                sa_dict = json.loads(fb.credentials)
                cred = credentials.Certificate(sa_dict)
                app = firebase_admin.initialize_app(
                    cred, {"databaseURL": fb.database_url}, name=name
                )
                try:
                    data = db.reference("devices", app=app).get()
                    if isinstance(data, dict):
                        return list(data.keys())
                    return []
                finally:
                    delete_app(app)
            else:
                base = self._normalize_url(fb.database_url)
                auth = f"?auth={fb.credentials}" if (fb.fb_type == "private_secret" and fb.credentials) else ""
                url = f"{base}/devices.json{auth}"
                r = requests.get(url, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, dict):
                        return list(data.keys())
                return []
        except Exception as e:
            logger.error(f"list_devices error: {e}")
            return []


firebase_manager = FirebaseManager()
