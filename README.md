# AdsBot — Multi-account Ads Automation

This repo implements a multi-user, multi-account Telegram AdsBot.

## Env vars (set on Heroku or local .env)
- BOT_TOKEN: your bot token
- OWNER_ID: numeric Telegram user id of owner/admin
- OWNER_LOGS_GROUP: numeric id (or @username) of channel/group where raw logs will be sent
- MONGO_URI: MongoDB connection string
- DB_NAME: optional (default adsbot)
- FORCE_CHANNEL, FORCE_GROUP: join links or @usernames
- UPI_ID, PAYMENT_QR_URL, PAYMENT_CONTACT
- START_IMAGE: URL of start image
- DEFAULT_DELAY_SECONDS
- RANDOMIZE_DELAY
- ADMINS: comma separated usernames (optional)

## Deploy
1. Create a MongoDB Atlas cluster and get MONGO_URI.
2. Push this repo to GitHub.
3. Connect Heroku app to GitHub and deploy.
4. Add config vars on Heroku (above env vars).
5. Scale worker dyno to 1.

## Notes
- Sessions are stored as StringSession in MongoDB (encrypted storage recommended in production).
- This tool can increase spam/bans risk — use responsibly.

#DEVLOPER-DEVIL @Ankitgupta214