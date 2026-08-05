import re
from typing import Dict, Any


def should_forward(sms_data: Dict[str, Any], filters: Dict) -> bool:
    if not filters:
        return True

    sender = str(sms_data.get("from") or sms_data.get("sender") or "").strip()
    body = str(
        sms_data.get("body")
        or sms_data.get("text")
        or sms_data.get("message")
        or ""
    )

    blacklist = filters.get("blacklist") or []
    if blacklist and any(b.lower() in sender.lower() for b in blacklist if b):
        return False

    whitelist = filters.get("whitelist") or []
    if whitelist:
        if not any(w.lower() in sender.lower() for w in whitelist if w):
            return False

    keywords = filters.get("keywords") or []
    if keywords:
        body_lower = body.lower()
        if not any(k.lower() in body_lower for k in keywords if k):
            return False

    regex_list = filters.get("regex") or []
    if regex_list:
        matched = False
        for pattern in regex_list:
            try:
                if re.search(pattern, body, re.IGNORECASE):
                    matched = True
                    break
            except re.error:
                continue
        if not matched:
            return False

    return True


def format_sms_message(device_id: str, sms_data: Dict[str, Any], fb_name: str = "") -> str:
    sender = sms_data.get("from") or sms_data.get("sender") or "Unknown"
    body = (
        sms_data.get("body")
        or sms_data.get("text")
        or sms_data.get("message")
        or ""
    )
    timestamp = (
        sms_data.get("timestamp")
        or sms_data.get("receivedAt")
        or sms_data.get("time")
        or ""
    )

    text = ""
    if fb_name:
        text += f"🔥 <b>Firebase:</b> {fb_name}\n"
    text += (
        f"📱 <b>Device:</b> <code>{device_id}</code>\n"
        f"👤 <b>From:</b> <code>{sender}</code>\n"
    )
    if timestamp:
        text += f"🕒 <b>Time:</b> {timestamp}\n"
    text += f"\n💬 <b>Message:</b>\n{body}"
    return text
