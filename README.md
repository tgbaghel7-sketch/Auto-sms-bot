# Firebase SMS → Telegram Bot (Simple Version)

Monitors your Firebase Realtime Database and forwards new SMS to a private Telegram channel.

**No encryption key needed** – only `BOT_TOKEN` is required.

## Expected Firebase Structure

```
/devices
  /{deviceId}
    /sms
      /{smsId}
        from: "+91xxxxxxxxxx"
        body: "Your OTP is 123456"
        timestamp: 1722...
```

---

## Deploy on Railway (Easiest)

### Step 1 – Put code on GitHub

1. Go to https://github.com → Sign in → **New repository**
2. Name it anything (example: `sms-bot`)
3. Click **Create repository**
4. On the next page click **uploading an existing file**
5. Drag **all files and folders** from this project into the browser and click **Commit changes**

### Step 2 – Deploy on Railway

1. Go to https://railway.app → Login with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select the repository you just created
4. Click **+ New** → **Database** → **Add PostgreSQL**
5. Click your **bot service** → **Variables** tab
6. Add only this variable:

```
BOT_TOKEN = your token from @BotFather
```

7. Also add (click **Add Variable Reference**):

```
DATABASE_URL → select Postgres → DATABASE_URL
```

8. Wait for deploy to finish. Open **Logs**.

You should see:
```
Database initialised
Bot starting (polling)…
```

### Step 3 – Use the bot

Open Telegram → search your bot → send `/start`

Then:
1. Connect Firebase (upload Service Account JSON)
2. Set Channel
3. Select Devices
4. Start Monitoring

---

## Local test (optional)

```bash
pip install -r requirements.txt
# create .env with BOT_TOKEN=...
python main.py
```

---

## Notes

- Only `BOT_TOKEN` is required.
- Credentials are stored in plain text in the database (do not share DB access).
- Bot must be admin of the private channel with "Post Messages" permission.
