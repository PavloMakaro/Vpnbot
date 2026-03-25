# Telegram Mini App VPN Bot

This repository contains the refactored code for the VPN bot, transitioning it from a standard Telegram bot into a Telegram Mini App utilizing MongoDB Atlas App Services (formerly Stitch).

## Project Structure

*   `bot_tma.py`: The lightweight Telegram bot entry point. Its only job is to serve the Web App button via the `/start` command.
*   `migrate_to_mongo.py`: Script to migrate legacy JSON data (`users.json`, `configs.json`, `payments.json`) to MongoDB.
*   `admin_tool.py`: CLI tool for bulk inserting VPN configurations into MongoDB.
*   `frontend/`: The frontend application built with vanilla JavaScript, Tailwind CSS, and the Realm Web SDK.
*   `backend/stitch/functions/`: The serverless functions deployed to MongoDB Atlas App Services.
*   `test_*.py`: Unit tests using `mongomock` to verify database scripts.

## Setup Instructions

### 1. MongoDB Setup
1. Create a MongoDB Atlas cluster.
2. Create a database named `vpn_bot` with three collections: `users`, `configs`, and `payments`.
3. Create an "App Service" (Realm) connected to this cluster.

### 2. Atlas App Services (Backend) Configuration
1. Go to your App Service -> Authentication -> Providers. Enable "Custom Function Authentication".
2. Set the custom authentication function to the code in `backend/stitch/functions/auth.js`.
3. Go to "Functions" and create the following functions, pasting the code from the respective files in `backend/stitch/functions/`:
    *   `getProfile`
    *   `getConfigs`
    *   `buySubscription`
    *   `createPayment`
    *   `checkPayment`
    *   `checkPendingPayments`
4. Set the authentication and authorization levels appropriately (typically requiring users to be logged in, except for `checkPendingPayments` which might be run via a trigger).
5. Go to "Values" (Environment Variables) and add:
    *   `BOT_TOKEN`: Your Telegram Bot Token.
    *   `YOOKASSA_SHOP_ID`: Your YooKassa Shop ID.
    *   `YOOKASSA_SECRET_KEY`: Your YooKassa Secret Key.

### 3. Frontend Deployment
1. Update `frontend/app.js` and set `APP_ID` to your MongoDB Realm App ID.
2. Host the `frontend` directory on any static hosting provider (e.g., GitHub Pages, Vercel, Netlify).
3. Ensure you have a valid HTTPS URL.

### 4. Telegram Bot Configuration
1. Talk to BotFather to create a new bot or update your existing one.
2. Set the Menu Button or Web App URL to the HTTPS URL where your frontend is hosted.
3. On your server, run the TMA Bot:
   ```bash
   pip install -r requirements.txt
   export BOT_TOKEN="your_bot_token"
   export WEB_APP_URL="your_frontend_url"
   python bot_tma.py
   ```

### 5. Migration (Optional)
If you have existing JSON data:
```bash
export MONGO_URI="your_mongodb_connection_string"
python migrate_to_mongo.py
```

### 6. Admin Tool
To bulk upload new configs:
```bash
export MONGO_URI="your_mongodb_connection_string"
python admin_tool.py 1_month configs_1_month.txt
```
