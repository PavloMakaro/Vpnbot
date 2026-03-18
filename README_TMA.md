# Telegram Mini App VPN Bot

This project uses a Telegram Mini App structure powered by MongoDB Atlas App Services (Stitch) as the backend, replacing the legacy long-polling Python approach.

## Architecture

- **Frontend:** Single Page Application (SPA) built with Vanilla JS and Tailwind CSS, utilizing the Realm Web SDK to communicate directly with MongoDB Atlas App Services.
- **Backend:** Serverless Atlas App Services Custom Functions managing business logic (Authentication, Subscriptions, Payments).
- **Entry Point Bot:** A lightweight Python bot (`bot_tma.py`) built with `aiogram` v3.x. Its sole purpose is to serve the Mini App URL to users via the `/start` command.
- **Database:** MongoDB Atlas `vpn_bot` database containing `users`, `configs`, and `payments` collections.

## Deployment Instructions for MongoDB Atlas App Services

### 1. Set Up MongoDB Atlas Cluster
1. Create a free cluster on MongoDB Atlas.
2. Create a database named `vpn_bot`.
3. Create collections: `users`, `configs`, and `payments`.

### 2. Configure Atlas App Services
1. Go to the "App Services" tab in Atlas and create a new App.
2. Navigate to **Authentication** -> **Providers** -> **Custom Function**.
3. Enable Custom Function Authentication.
4. Set the authentication function to `auth.js` (copy the code from `backend/stitch/functions/auth.js`).

### 3. Set Context Values (Environment Variables)
Navigate to **Values & Secrets** in the left sidebar and create the following Context Values:
1. `BOT_TOKEN` (Type: Secret) - Your Telegram Bot Token.
2. `YOOKASSA_SHOP_ID` (Type: Value) - Your Yookassa Shop ID.
3. `YOOKASSA_SECRET_KEY` (Type: Secret) - Your Yookassa Secret Key.

### 4. Create Backend Functions
Navigate to **Functions** and create the following functions, pasting the code from the `backend/stitch/functions` directory:
- `auth` (System)
- `getProfile` (User)
- `getConfigs` (User)
- `buySubscription` (User)
- `createPayment` (User)
- `checkPayment` (User)
- `checkPendingPayments` (User)

### 5. Frontend Integration
1. Replace `YOUR_REALM_APP_ID` in `frontend/app.js` with your actual Atlas App ID (found in the top left corner of the App Services dashboard).
2. Host the `frontend` folder statically (e.g., GitHub Pages, Vercel, Netlify).
3. Set your hosted URL as the `WEB_APP_URL` environment variable for your Python entry bot.

## Python Scripts

- `bot_tma.py`: The entry point for the bot. Set `BOT_TOKEN` and `WEB_APP_URL` environment variables before running.
- `migrate_to_mongo.py`: Run this script locally to migrate data from the legacy JSON files (`users.json`, `configs.json`, `payments.json`) to your MongoDB Atlas cluster. Set the `MONGO_URI` environment variable before running.
- `admin_tool.py`: A CLI tool for bulk uploading configuration links to MongoDB. Set the `MONGO_URI` environment variable before running.

## Running Tests
To verify database interaction scripts, install dependencies from `requirements.txt` and run:
```bash
python -m unittest test_migration.py test_admin.py
```
