# Telegram Mini App VPN Bot

This project converts a legacy Telegram Bot into a modern Telegram Mini App (TMA) using MongoDB Atlas App Services (formerly Stitch).

## Architecture

- **Frontend:** HTML/JS/TailwindCSS (Single Page Application).
- **Backend:** MongoDB Atlas App Services (Serverless Functions).
- **Database:** MongoDB Atlas.
- **Bot:** Python (`aiogram`) for serving the Mini App and Admin tools.

## Setup Instructions

### 1. MongoDB Atlas Setup

1.  Create a MongoDB Atlas account and a new Cluster (Free Tier is fine).
2.  Create a Database User (username/password) and allow network access (0.0.0.0/0 for testing, or specific IPs).
3.  Get your Connection String (`mongodb+srv://...`).

### 2. Atlas App Services (Stitch) Setup

1.  Go to the "App Services" tab in Atlas and create a new App.
2.  Link it to your Cluster.
3.  **Authentication:**
    - Enable "Custom Function Authentication".
    - Upload `backend/stitch/functions/auth.js` as the auth function.
    - Set a Secret Value named `TELEGRAM_BOT_TOKEN` with your Bot Token.
4.  **Functions:**
    - Create the following functions (copy content from `backend/stitch/functions/`):
        - `getUser`
        - `getConfigs`
        - `createPayment`
        - `checkPayment`
        - `buySubscription`
        - `getMyConfigs`
    - **Settings:** Ensure `getUser`, `createPayment`, etc., run as "System" or have proper Rules.
    - **Values (Secrets):**
        - Create `YOOKASSA_SHOP_ID`
        - Create `YOOKASSA_SECRET_KEY`

### 3. Frontend Deployment

1.  Host the `frontend/` folder on a static hosting service (GitHub Pages, Netlify, Vercel).
2.  Open `frontend/app.js` and replace `APP_ID` with your Atlas App ID.
3.  Get the public URL (e.g., `https://your-site.netlify.app`).

### 4. Telegram Bot Setup

1.  Create a bot with @BotFather.
2.  Set the Menu Button URL to your Frontend URL (or just use the `/start` command link).
3.  Set up the Python bot:
    ```bash
    pip install -r requirements.txt
    ```
4.  Run the bot:
    ```bash
    export BOT_TOKEN="your_bot_token"
    export MONGODB_URI="your_mongo_uri"
    export ADMIN_ID="your_telegram_id"
    export WEBAPP_URL="https://your-frontend-url.com"
    python bot_tma.py
    ```

### 5. Data Migration (Optional)

If you have `users.json` etc. from the old bot:
1.  Place them in the root directory.
2.  Run:
    ```bash
    export MONGODB_URI="your_mongo_uri"
    python migrate_to_mongo.py
    ```

## Logic Flow

1.  User opens Bot -> Click "Open App".
2.  Frontend initializes -> Gets `initData` from Telegram.
3.  Frontend calls `realmApp.logIn` -> Calls Atlas `auth` function.
4.  `auth` verifies `initData` signature -> Logs user in.
5.  Frontend calls `getUser` -> Displays balance/sub.
6.  User clicks "Topup" -> `createPayment` -> Yookassa Link.
7.  User pays -> Webhook or "Check Status" updates DB.
8.  User clicks "Buy VPN" -> `buySubscription` -> Deducts balance -> Assigns config.
