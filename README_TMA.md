# VPN Telegram Mini App Architecture

This repository outlines the migration from a legacy Python Telegram bot to a Single Page Application (SPA) driven Telegram Mini App (TMA).

## Architecture

* **Frontend:** Built with vanilla JS and Tailwind CSS, authenticated via the Realm Web SDK.
* **Backend:** Serverless JavaScript functions orchestrated by MongoDB Atlas App Services (Stitch).
* **Database:** MongoDB (`vpn_bot` database).
* **Telegram Bot Entry:** `bot_tma.py` running on `aiogram` v3.x simply hosts the Mini App launch button.

## Deployment Instructions

### 1. MongoDB Atlas Setup
1. Create an Atlas Cluster and create a database named `vpn_bot` containing three collections: `users`, `configs`, and `payments`.
2. Navigate to the "App Services" tab and create a new App. Note the **App ID**.
3. Replace `YOUR_ATLAS_APP_ID` in `frontend/app.js` with your real App ID.

### 2. Atlas App Services Configuration
1. **Authentication:**
   - Enable "Custom Function Authentication".
   - Create a new function, insert the contents of `backend/stitch/functions/auth.js`.
2. **Context Values (Secrets):**
   - Create a value named `BOT_TOKEN` (Secret type).
   - Create a value named `YOOKASSA_SHOP_ID`.
   - Create a value named `YOOKASSA_SECRET_KEY` (Secret type).
3. **Functions:**
   - Create the remaining functions (`getProfile`, `getConfigs`, `buySubscription`, `createPayment`, `checkPayment`, `checkPendingPayments`) found in `backend/stitch/functions/`. Ensure they run as "System" or have the correct rules configured to interact with the database.

### 3. Data Migration
1. Set the `MONGO_URI` environment variable pointing to your Atlas cluster.
2. Run `python migrate_to_mongo.py` in the directory alongside your legacy `users.json`, `configs.json`, and `payments.json`.

### 4. Bot Launch
1. Ensure your `BOT_TOKEN` and `WEB_APP_URL` (where you host the `frontend/` folder) are set as environment variables.
2. Run the bot: `python bot_tma.py`.