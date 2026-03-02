# VPN Mini App

This project converts a legacy Telegram Bot into a full Telegram Mini App (TMA). It uses a serverless architecture with **MongoDB Atlas App Services** for the backend, **Vanilla JS / Tailwind** for the frontend, and **Aiogram v3** for the entrypoint bot.

## Architecture

- **Backend (Stitch)**: Serverless JavaScript functions hosted on MongoDB Atlas App Services.
- **Frontend**: Single Page Application hosted anywhere (GitHub Pages, Vercel, Netlify).
- **Bot**: Python (Aiogram v3) bot that serves the `/start` command containing the Web App button.
- **Database**: MongoDB Atlas containing `users`, `configs`, and `payments` collections.

## Setup Instructions

### 1. MongoDB Atlas App Services
1. Create a MongoDB cluster and create a database named `vpn_bot`.
2. Create three collections: `users`, `configs`, `payments`.
3. Create an Atlas App Service.
4. Go to **Authentication** -> Enable **Custom Function Authentication**. Select the `auth` function.
5. Create the following functions from the `backend/stitch/functions/` directory:
   - `auth.js`
   - `getProfile.js`
   - `getConfigs.js`
   - `buySubscription.js`
   - `createPayment.js`
   - `checkPayment.js`
6. Create **Context Values**:
   - `BOT_TOKEN`: Your Telegram Bot Token (Secret)
   - `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID (Value)
   - `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key (Secret)

### 2. Frontend
1. Open `frontend/app.js` and replace `REALM_APP_ID` with your actual Atlas App ID.
2. Host the `frontend/` directory on a static file hosting service.

### 3. Telegram Bot
1. Ensure your bot's `/start` command points to the hosted frontend URL.
2. Run the bot:
   ```bash
   export BOT_TOKEN="your_token"
   export WEB_APP_URL="https://your-frontend-url.com"
   python3 bot_tma.py
   ```

### 4. Data Migration
To migrate from legacy JSON files (`users.json`, `configs.json`, `payments.json`):
```bash
export MONGO_URI="mongodb+srv://user:pass@cluster.mongodb.net"
python3 migrate_to_mongo.py
```

### 5. Admin Tool
To bulk upload VPN configurations:
```bash
export MONGO_URI="mongodb+srv://user:pass@cluster.mongodb.net"
python3 admin_tool.py 1_month configs.txt
```