# Telegram Mini App VPN Bot - MongoDB Atlas Migration

This repository contains the source code for the VPN Telegram Mini App, migrating from a legacy JSON-based backend to a modern stack utilizing MongoDB Atlas App Services (formerly Stitch).

## Project Structure

- `frontend/`: Contains the Single Page Application (SPA) utilizing HTML, Tailwind CSS, and vanilla JS. It integrates with the Telegram WebApp and Realm Web SDK.
- `backend/stitch/functions/`: JavaScript serverless functions intended to be deployed to MongoDB Atlas App Services.
- `bot_tma.py`: A lightweight aiogram v3 bot that serves the Telegram WebApp link.
- `migrate_to_mongo.py`: Script to migrate existing legacy `users.json`, `configs.json`, and `payments.json` into MongoDB.
- `admin_tool.py`: CLI tool for administrators to bulk upload new configurations to the MongoDB database.
- `ai_studio_code.py` / `server_backup_bot.py`: Maintained legacy code for reference or continued fallback use.

## Prerequisites

- MongoDB Atlas Account
- App Services App linked to your cluster
- Node.js (if deploying Stitch via CLI)
- Python 3.9+
- Yookassa Merchant Account
- Telegram Bot Token

## Deployment Instructions

### 1. MongoDB Atlas App Services Setup
1. Create a new App in MongoDB Atlas.
2. Link it to your `vpn_bot` database cluster.
3. In the App Services UI, navigate to **Custom Authentication** and enable it.
   - Use the function logic provided in `backend/stitch/functions/auth.js`.
4. Create the following **Functions** in the App Services UI, copying the code from `backend/stitch/functions/`:
   - `getProfile`
   - `getConfigs`
   - `buySubscription`
   - `createPayment`
   - `checkPayment`
   - `checkPendingPayments`
5. Configure **Values & Secrets** in App Services:
   - `BOT_TOKEN`: Your Telegram bot token (Secret).
   - `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID.
   - `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key (Secret).

### 2. Frontend Configuration
Edit `frontend/app.js` and set the `REALM_APP_ID` variable to your new MongoDB Atlas App ID. Deploy the `frontend/` directory to any static hosting provider (e.g., GitHub Pages, Vercel, Netlify).

### 3. Telegram Bot Setup
Run the `bot_tma.py` script. Ensure you provide the necessary environment variables:
```bash
export BOT_TOKEN="your_telegram_bot_token"
export TMA_URL="https://your-deployed-frontend-url.com"
pip install -r requirements.txt
python bot_tma.py
```

### 4. Data Migration
To migrate your existing data from the JSON files to MongoDB:
```bash
export MONGO_URI="mongodb+srv://<user>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority"
pip install pymongo
python migrate_to_mongo.py
```

### 5. Managing Configurations
To add new VPN configurations to the database:
```bash
export MONGO_URI="mongodb+srv://<user>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority"
python admin_tool.py 1_month vless://example1 vless://example2
```

## Security Notes
- The `auth.js` function securely validates the Telegram `initData` hash. Do not modify it to accept static test data in production.
- Environment variables must be used. Hardcoded tokens are prohibited.
