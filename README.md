# Multi-Firebase SMS → Telegram Bot

Monitor **multiple** Firebase Realtime Databases (public or private) and forward SMS to your Telegram channels.

## Features

- Multiple Firebase accounts per user
- **Public** Firebase → only URL needed
- **Private** Firebase → Service Account JSON **or** URL + Database Secret
- Multiple channels – select which one receives SMS
- Device selection, filters, start/stop forwarding
- Auto-restore listeners after Railway restart

## Menu

```
Main Menu
├── 🔥 Manage Firebase  → Add / Delete / Select / List
├── 📱 Device           → Add / Remove / List
├── 📢 Manage Channel   → Add / Remove / Select / List
├── 🔍 Filters          → Keywords, Regex, Whitelist, Blacklist
├── ▶️ Start / ⏹ Stop Forwarding
└── 📊 Status
```

## Expected Firebase path

```
/devices/{deviceId}/sms/{smsId}
  from, body, timestamp
```

## Deploy on Railway

1. Upload this folder to GitHub
2. Railway → New Project → Deploy from GitHub
3. Add PostgreSQL plugin
4. Variables on bot service:
   - `BOT_TOKEN` = your token
   - `DATABASE_URL` = reference → Postgres DATABASE_URL
5. Start command: `python main.py`

## Local

```bash
pip install -r requirements.txt
# .env with BOT_TOKEN=...
python main.py
```
