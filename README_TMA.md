# VPN Bot - Telegram Mini App (TMA)

This project is a Telegram Mini App for selling VPN subscriptions, built using MongoDB Atlas App Services (formerly Stitch) for the backend and a simple HTML/JS frontend.

## Architecture

*   **Frontend**: Single Page Application (SPA) hosted on MongoDB App Services Hosting or GitHub Pages. Uses `telegram-web-app.js` and `realm-web`.
*   **Backend**: Serverless JavaScript functions running on MongoDB Atlas App Services.
*   **Database**: MongoDB Atlas (`users`, `configs`, `payments` collections).
*   **Bot**: A lightweight Python bot (`bot_tma.py`) to launch the Web App.

## Deployment Steps

### 1. MongoDB Atlas Setup

1.  Create a free Cluster on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2.  Create a Database named `vpn_bot`.
3.  Create 3 collections: `users`, `configs`, `payments`.
4.  Go to **App Services** tab -> Create a new App.
5.  Link your Cluster to the App.

### 2. Configure App Services

1.  **Authentication**: Enable **Custom Function Authentication**.
2.  **Values & Secrets**:
    *   Create a Secret named `bot_token_secret` with your Telegram Bot Token.
    *   Create a Value named `BOT_TOKEN` linked to that secret.
    *   Create Secrets for `yookassa_shop_id` and `yookassa_secret_key`.
    *   Create Values `YOOKASSA_SHOP_ID` and `YOOKASSA_SECRET_KEY` linked to them.
3.  **Functions**:
    *   Copy the contents of `backend/stitch/functions/` to your App Service functions.
    *   Ensure function names match the filenames (e.g., `auth`, `getProfile`, `buySubscription`).
    *   Set authentication for `auth` to "System" (or allow anonymous execution if needed, but Custom Auth handles validation).
    *   Set authentication for other functions (`getProfile`, `buySubscription`, etc.) to "Application Authentication" (require logged-in user).

### 3. Deploy Frontend

1.  Go to **Hosting** in App Services side menu.
2.  Upload the files from `frontend/` (`index.html`, `styles.css`, `app.js`).
3.  **Important**: Open `frontend/app.js` and replace `REALM_APP_ID` with your actual App ID (found in App Services dashboard).
4.  Deploy the hosting. Note the URL (e.g., `https://<app-id>.mongodbstitch.com`).

### 4. Data Migration

1.  Ensure you have your old `users.json`, `configs.json`, `payments.json` in the root folder.
2.  Install dependencies: `pip install pymongo`
3.  Set your MongoDB Connection String: `export MONGO_URI="mongodb+srv://..."`
4.  Run migration: `python migrate_to_mongo.py`

### 5. Launch Bot

1.  Install dependencies: `pip install aiogram`
2.  Set environment variable: `export BOT_TOKEN="your_token"`
3.  Update `bot_tma.py` with your Web App URL.
4.  Run the bot: `python bot_tma.py`

## Admin Tools

*   Use `admin_tool.py` (to be created) to upload new configs in bulk.
*   Use MongoDB Compass or Atlas UI to manage users/payments manually if needed.

## Notes

*   Ensure your Yookassa Return URL points to your bot (e.g., `https://t.me/your_bot`).
*   The `auth` function validates Telegram's `initData` hash to prevent spoofing.
