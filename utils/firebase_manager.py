import json
import logging
import threading
from typing import Dict, Optional, Callable, List
import firebase_admin
from firebase_admin import credentials, db, delete_app
from utils.encryption import decrypt
from models import User

logger = logging.getLogger(__name__)


class FirebaseManager:
    """
    Manages one Firebase app + listeners per Telegram user.
    Strict isolation – each user only ever touches their own credentials.
    """

    def __init__(self):
        self._apps: Dict[int, firebase_admin.App] = {}
        self._listeners: Dict[int, list] = {}
        self._lock = threading.Lock()
        # Store the last callback so we can restart listeners after process restart
        self._on_sms_callback: Optional[Callable] = None

    def set_callback(self, callback: Callable):
        """Set the global SMS callback used by all listeners."""
        self._on_sms_callback = callback

    def _create_app(self, user: User) -> Optional[firebase_admin.App]:
        """Create a dedicated Firebase app for this user only."""
        try:
            name = f"user_{user.telegram_id}"

            # Clean previous if exists
            try:
                old = firebase_admin.get_app(name)
                delete_app(old)
            except ValueError:
                pass

            if user.firebase_type == "service_account":
                sa_json = decrypt(user.firebase_service_account)
                sa_dict = json.loads(sa_json)
                cred = credentials.Certificate(sa_dict)

                url = None
                if user.firebase_url:
                    url = decrypt(user.firebase_url)
                if not url:
                    url = sa_dict.get("databaseURL") or sa_dict.get("database_url")
                if not url:
                    raise ValueError(
                        "No databaseURL found. Please set it when uploading the Service Account JSON."
                    )

                app = firebase_admin.initialize_app(
                    cred, {"databaseURL": url}, name=name
                )

            elif user.firebase_type == "secret":
                # firebase-admin no longer supports Database Secrets for real-time listeners.
                raise ValueError(
                    "Database Secret method is not supported by firebase-admin. "
                    "Please use Service Account JSON."
                )
            else:
                raise ValueError("Unknown firebase_type")

            return app
        except Exception as e:
            logger.error(
                f"Failed to create Firebase app for user {user.telegram_id}: {e}"
            )
            return None

    def start_listening(self, user: User, on_sms_callback: Callable = None) -> bool:
        """
        Start real-time listeners for all selected devices of this user.
        on_sms_callback(telegram_id, device_id, sms_data, path)
        """
        callback = on_sms_callback or self._on_sms_callback
        if not callback:
            logger.error("No SMS callback registered")
            return False

        with self._lock:
            # Stop previous listeners first
            self._stop_listening_unlocked(user.telegram_id)

            app = self._create_app(user)
            if not app:
                return False

            self._apps[user.telegram_id] = app
            self._listeners[user.telegram_id] = []

            if not user.selected_devices:
                logger.info(f"User {user.telegram_id} has no selected devices")
                return True

            for device_id in list(user.selected_devices):
                try:
                    ref = db.reference(f"devices/{device_id}/sms", app=app)

                    def make_callback(dev_id: str, tid: int):
                        def _cb(event):
                            # Only react to new/updated data
                            if event.event_type in ("put", "patch") and event.data is not None:
                                try:
                                    callback(tid, dev_id, event.data, event.path)
                                except Exception as e:
                                    logger.error(f"SMS callback error: {e}")

                        return _cb

                    listener = ref.listen(make_callback(device_id, user.telegram_id))
                    self._listeners[user.telegram_id].append(listener)
                    logger.info(
                        f"Started listener for user {user.telegram_id} device {device_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to start listener for device {device_id}: {e}"
                    )

            return True

    def _stop_listening_unlocked(self, telegram_id: int):
        listeners = self._listeners.pop(telegram_id, [])
        for reg in listeners:
            try:
                reg.close()
            except Exception:
                pass

        app = self._apps.pop(telegram_id, None)
        if app:
            try:
                delete_app(app)
            except Exception:
                pass

    def stop_listening(self, telegram_id: int):
        with self._lock:
            self._stop_listening_unlocked(telegram_id)
            logger.info(f"Stopped all listeners for user {telegram_id}")

    def is_listening(self, telegram_id: int) -> bool:
        return (
            telegram_id in self._listeners
            and len(self._listeners[telegram_id]) > 0
        )

    def get_devices(self, user: User) -> List[str]:
        """Return list of device IDs under /devices for this user."""
        app = self._create_app(user)
        if not app:
            return []
        try:
            ref = db.reference("devices", app=app)
            data = ref.get()
            if isinstance(data, dict):
                return list(data.keys())
            return []
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []
        finally:
            try:
                delete_app(app)
            except Exception:
                pass

    def stop_all(self):
        """Called on shutdown."""
        with self._lock:
            ids = list(self._apps.keys())
            for tid in ids:
                self._stop_listening_unlocked(tid)
            logger.info("All Firebase listeners stopped")


# Global singleton
firebase_manager = FirebaseManager()
