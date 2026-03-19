# VPN Telegram Mini App

This project converts the legacy python-based VPN Bot into a modern Telegram Mini App.
It uses MongoDB Atlas App Services (Stitch) for the backend and a pure HTML/JS frontend using the Realm SDK.

## Architecture

- **Frontend**: A Single Page Application (SPA) using HTML, vanilla JavaScript, and Tailwind CSS. Hosted anywhere (e.g., GitHub Pages, Cloudflare Pages, Vercel).
- **Backend**: MongoDB Atlas App Services functions (`backend/stitch/functions`).
- **Database**: MongoDB collection (`vpn_bot.users`, `vpn_bot.configs`, `vpn_bot.payments`).
- **Entry Point**: A simple aiogram Python bot (`bot_tma.py`) to serve the Web App link.

## Deployment Instructions

### 1. MongoDB Atlas App Services Setup
1. Create a MongoDB Atlas account and cluster.
2. Create an App Service linked to your cluster.
3. In the App Service UI, go to **Authentication** and enable **Custom Function Authentication**.
   - Create a new function called `auth` and copy the code from `backend/stitch/functions/auth.js`.
4. Go to **Values** (or **Environment Variables** / **Secrets** in newer UI). Add the following:
   - `BOT_TOKEN` (Secret): Your Telegram bot token. (Important for validating initData)
   - `YOOKASSA_SHOP_ID` (Value): Your YooKassa Shop ID.
   - `YOOKASSA_SECRET_KEY` (Secret): Your YooKassa Secret Key.
5. Go to **Functions**. Create all the functions matching the names and code found in `backend/stitch/functions/`:
   - `getProfile`
   - `getConfigs`
   - `buySubscription`
   - `createPayment`
   - `checkPayment`
   - `checkPendingPayments`
   Make sure to configure the authorization settings for these functions so that only authenticated users can execute them.
6. Note your **Realm App ID**. You will need this for the frontend.

### 2. Frontend Deployment
1. Edit `frontend/app.js` and replace `REALM_APP_ID` with your actual Realm App ID from step 1.
2. Host the `frontend` directory on any static hosting service (e.g., Vercel, Netlify, Cloudflare Pages, GitHub Pages). Note the URL.

### 3. Telegram Bot Entry Point
1. Run the Telegram bot script to serve the Web App button to your users.
   ```bash
   export BOT_TOKEN="your-telegram-bot-token"
   export WEBAPP_URL="https://your-frontend-url.com"
   python bot_tma.py
   ```

### 4. Data Migration
If you are coming from the legacy JSON-based system, you can migrate your existing data to MongoDB:
1. Export your MongoDB connection string to `MONGO_URI`.
   ```bash
   export MONGO_URI="mongodb+srv://username:password@cluster.mongodb.net"
   ```
2. Place your old `users.json`, `configs.json`, and `payments.json` files in the same directory.
3. Run the migration script:
   ```bash
   pip install -r requirements.txt
   python migrate_to_mongo.py
   ```

### 5. Admin Tools
To upload new VPN configs in bulk to MongoDB, use the admin tool:
```bash
python admin_tool.py <period> <link1> <link2> ...
# Example
python admin_tool.py 1_month "vless://abc..." "vless://def..."
```