# VPN Bot - Telegram Mini App (TMA)

This repository contains a modern Telegram Mini App (TMA) architecture for a VPN service, replacing the legacy bot implementation.

## Architecture

* **Frontend:** A responsive Single Page Application (SPA) built with vanilla JS and Tailwind CSS, utilizing the Telegram WebApp JS SDK.
* **Backend:** MongoDB Atlas App Services (Stitch), providing serverless functions and data synchronization using the Realm Web SDK.
* **Database:** MongoDB Atlas, storing `users`, `configs`, and `payments`.
* **Bot Entry Point:** A lightweight `aiogram` bot (`bot_tma.py`) that serves the Web App link via inline keyboards on `/start`.

## Setup & Deployment

### 1. Database & Atlas App Services
1. Create a MongoDB Atlas Cluster and a database named `vpn_bot`.
2. Create an Atlas App Service connected to this database.
3. Enable **Custom Function Authentication** in App Services.
4. Add the functions from `backend/stitch/functions/` to your Atlas App.
5. In App Services, create the following **Values & Secrets**:
   - `BOT_TOKEN`: Your Telegram Bot API Token.
   - `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID.
   - `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key.

### 2. Frontend
1. Open `frontend/app.js` and replace `APP_ID` with your actual Atlas App ID.
2. Host the contents of the `frontend/` directory on a secure HTTPS server (e.g., Vercel, Netlify, GitHub Pages).

### 3. Telegram Bot
1. Install Python dependencies: `pip install -r requirements.txt`.
2. Set environment variables:
   ```bash
   export BOT_TOKEN="your_bot_token"
   export WEB_APP_URL="https://your-frontend-domain.com"
   ```
3. Run the bot: `python bot_tma.py`
4. Use `@BotFather` to set the "Menu Button" URL to your `WEB_APP_URL` if desired.

### 4. Migration (Legacy to Mongo)
If migrating from the legacy JSON file structure (`users.json`, `configs.json`, `payments.json`):
1. Place the JSON files in the project root.
2. Set your MongoDB connection string:
   ```bash
   export MONGO_URI="mongodb+srv://user:pass@cluster.net/?retryWrites=true&w=majority"
   ```
3. Run the migration script: `python migrate_to_mongo.py`

### 5. Admin Tools
To bulk upload new VPN configs:
```bash
export MONGO_URI="..."
python admin_tool.py configs_file.txt 1_month
```