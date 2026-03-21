# Deployment Instructions

## Atlas App Services (Stitch)
1. Create a MongoDB Atlas cluster.
2. Go to the "App Services" tab and create a new App.
3. Link your Atlas cluster to the App.
4. Enable "Custom Function Authentication".
5. In the "Functions" section, create the functions from the `backend/stitch/functions/` directory (`auth`, `getProfile`, `getConfigs`, `buySubscription`, `createPayment`, `checkPayment`, `checkPendingPayments`).
6. Set the `auth` function as the Custom Function Authentication handler.
7. In the "Values" section (Context Values), add the following secrets:
    * `BOT_TOKEN`: Your Telegram Bot Token.
    * `YOOKASSA_SHOP_ID`: Your YooKassa Shop ID.
    * `YOOKASSA_SECRET_KEY`: Your YooKassa Secret Key.
8. Get your Realm App ID (found in the top left corner of the App Services dashboard).

## Frontend
1. Open `frontend/app.js` and replace `YOUR_APP_ID` with your actual Realm App ID.
2. Host the `frontend/` directory on a static file hosting service (e.g., GitHub Pages, Vercel, Netlify).

## Python Bot Setup
1. Set the environment variables:
    * `BOT_TOKEN`: Your Telegram Bot Token.
    * `WEB_APP_URL`: The URL where your frontend is hosted.
2. Run the `bot_tma.py` script: `python bot_tma.py`

## Data Migration
1. Ensure your local `users.json`, `configs.json`, and `payments.json` are in the same directory as the script.
2. Run `python migrate_to_mongo.py --uri "YOUR_MONGODB_CONNECTION_STRING" --db vpn_bot`
