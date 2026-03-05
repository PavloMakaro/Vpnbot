# VPN Bot TMA - Deployment Instructions

This project is a Telegram Mini App (TMA) for purchasing VPN subscriptions, using MongoDB Atlas App Services (formerly Stitch) for the backend and a lightweight vanilla JS frontend.

## 1. MongoDB Atlas Setup

1. Create a MongoDB Atlas account and cluster.
2. Create a database named `vpn_bot` with the following collections:
   - `users`
   - `configs`
   - `payments`

## 2. Atlas App Services (Stitch) Setup

1. Go to the "App Services" tab in Atlas and create a new App.
2. Link your Atlas cluster to the App.

### 2.1 Context Values (Secrets)
Set up the following Context Values in your App Services dashboard (under Build > Values):
- `BOT_TOKEN`: Your Telegram Bot Token (used for validating TMA authentication).
- `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID.
- `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key.

### 2.2 Functions
Import all JavaScript files from `backend/stitch/functions/` into your App Services Functions section.
- `auth`: (Use for Custom Function Authentication).
- `getProfile`
- `getConfigs`
- `buySubscription`
- `createPayment`
- `checkPayment`

Ensure the functions have permission to read/write the linked MongoDB cluster.

### 2.3 Authentication
1. Go to Authentication > Providers.
2. Enable "Custom Function Authentication".
3. Select the `auth` function as the auth function.

## 3. Frontend Deployment

1. The frontend files are located in `frontend/`.
2. Host the `frontend/` directory on any static file host (e.g., GitHub Pages, Cloudflare Pages, Vercel, Netlify).
3. Ensure the hosted URL uses HTTPS.

### 3.1 Link Frontend to Realm
In `frontend/app.js`, update the `REALM_APP_ID` constant with your actual Atlas App Services App ID.

## 4. Telegram Bot Setup

1. Set your Bot's Web App URL via BotFather or deploy `bot_tma.py` on a server.
2. If using `bot_tma.py`, run:
   ```bash
   export BOT_TOKEN="your_telegram_bot_token"
   python3 bot_tma.py
   ```
   *Note: `bot_tma.py` simply serves the link to the Mini App.*

## 5. Migration (Optional)

If migrating from the legacy JSON-based bot (`users.json`, `configs.json`, `payments.json`), run `migrate_to_mongo.py`.
```bash
export MONGO_URI="your_mongodb_connection_string"
python3 migrate_to_mongo.py
```