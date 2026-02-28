# VPN Telegram Mini App

This project converts the legacy long-polling Telegram Bot to a Telegram Mini App architecture, backed by MongoDB Atlas App Services (Stitch).

## Features
- SPA Frontend using Tailwind CSS and Realm Web SDK.
- Telegram Mini App interface.
- Complete backend logic ported to MongoDB Atlas Serverless Functions.
- Secure, tokenless Yookassa integration via context values.
- Centralized Data Migration from Legacy JSONs (`users.json`, `configs.json`, `payments.json`).

## 1. Prerequisites
- MongoDB Atlas Account with a free-tier cluster (`M0` or higher).
- Atlas App Services Application linked to your cluster.
- Telegram Bot Token from `@BotFather`.
- Yookassa Shop ID and Secret Key.

## 2. Setting Up the Database
Create a database named `vpn_bot_db` with three collections:
- `users`
- `configs`
- `payments`

### Running the Migration (Legacy to Mongo)
To migrate data from your legacy local JSON files to MongoDB:
```bash
export MONGO_URI="mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
export MONGO_DB_NAME="vpn_bot_db"
python3 migrate_to_mongo.py
```

### Admin Tool (Bulk Config Upload)
To bulk upload new configs into the MongoDB `configs` collection securely:
```bash
export MONGO_URI="mongodb+srv://..."
python3 admin_tool.py <1_month|2_months|3_months> <path_to_txt_file_with_links>
```

## 3. Setting Up Atlas App Services (Backend)

### 3.1. Context Values (Secrets)
Navigate to **Values** in your App Services dashboard and add the following securely:
- `BOT_TOKEN`: Your Telegram Bot Token (Type: Value or Secret).
- `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID.
- `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key.

### 3.2. Authentication Provider
Navigate to **Authentication -> Custom Function Authentication**.
- **Enable** Custom Function Authentication.
- Choose **Create New Function** and paste the code from `backend/stitch/functions/auth.js`.
- Name it `auth`.

### 3.3. Functions
Navigate to **Functions** and create the following functions, pasting the respective codes from `backend/stitch/functions/`:
1. `getProfile` (Authentication: System/User)
2. `getConfigs` (Authentication: System/User)
3. `buySubscription` (Authentication: System/User)
4. `createPayment` (Authentication: System/User)
5. `checkPayment` (Authentication: System/User)

## 4. Setting Up the Frontend
1. Open `frontend/app.js`.
2. Replace `YOUR_REALM_APP_ID` with your actual Atlas App ID found in your dashboard.
3. Host the `frontend` directory on any static file host (e.g., GitHub Pages, Netlify, Vercel).

## 5. Setting Up the Telegram Bot
1. Export the Bot Token and Web App URL in your environment:
```bash
export BOT_TOKEN="your_telegram_bot_token"
export WEB_APP_URL="https://your-hosted-frontend.com/index.html"
```
2. Run the bot:
```bash
python3 bot_tma.py
```