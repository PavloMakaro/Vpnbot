# VPN Mini App Deployment Guide

This guide describes how to deploy the Telegram Mini App (TMA) version of the VPN bot, which uses MongoDB Atlas App Services (Stitch) for the backend and Realm Web SDK for the frontend.

## Architecture
- **Frontend**: Vanilla JS Single Page Application (SPA) using Tailwind CSS and Realm Web SDK.
- **Backend**: MongoDB Atlas App Services (Stitch) functions.
- **Database**: MongoDB Atlas.
- **Entry Bot**: `bot_tma.py` using `aiogram` to serve the Web App link.

## Deployment Steps

### 1. MongoDB Atlas Setup
1. Create a MongoDB Atlas cluster.
2. Create a database named `vpn_bot` with collections: `users`, `configs`, `payments`.
3. Create an Atlas App Services App.
4. Go to **Authentication** -> **Custom Function**. Use the code from `backend/stitch/functions/auth.js`.
5. Create the remaining backend functions from the `backend/stitch/functions/` directory.

### 2. Context Values
Set the following Context Values in Atlas App Services (Values -> Context Values):
- `BOT_TOKEN`: Your Telegram bot token (Plain text or Secret).
- `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID.
- `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key.

### 3. Frontend Deployment
1. Replace `YOUR_ATLAS_APP_ID` in `frontend/app.js` with your actual Atlas App ID.
2. Host the `frontend/` directory on a static web host (e.g., GitHub Pages, Vercel, Netlify).

### 4. Running the Entry Bot
1. Install requirements: `pip install -r requirements.txt`
2. Set environment variables:
   - `export BOT_TOKEN="your_telegram_bot_token"`
   - `export WEBAPP_URL="https://your-frontend-url.com"`
3. Run the bot: `python bot_tma.py`

### 5. Utilities
- **Data Migration**: To migrate from the legacy JSON files (`users.json`, `configs.json`, `payments.json`) to MongoDB, ensure `MONGO_URI` is set and run: `python migrate_to_mongo.py`.
- **Bulk Upload Configs**: Use the admin tool to bulk upload config links to the database:
  `python admin_tool.py --period 1_month --file links.txt`
