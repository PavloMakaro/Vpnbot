# Deployment Guide for VPN Bot Mini App

This guide explains how to deploy the Telegram Mini App using MongoDB Atlas App Services (formerly Stitch) and Yookassa.

## 1. MongoDB Atlas Setup

1.  **Create a Cluster**: Sign up for MongoDB Atlas and create a free cluster.
2.  **Create App Service**: Go to the "App Services" tab and create a new App.
3.  **Link Database**: Link your cluster and use the database name `vpn_bot`.

## 2. Configure App Services

### Authentication
1.  Go to **Authentication** > **Authentication Providers**.
2.  Enable **Custom Function Authentication**.
3.  Select the `auth` function (we will create it next) as the authentication function.

### Functions
1.  Go to **Functions**.
2.  Create the following functions and paste the code from `backend/stitch/functions/`:
    *   `auth`: Validates Telegram initData.
    *   `getUserProfile`: Fetches user data.
    *   `buySubscription`: Handles purchases.
    *   `createPayment`: Generates Yookassa payment URL.
    *   `getConfigs`: Returns user configs.
    *   Make sure to set the authentication to "System" or "Application Authentication" as appropriate (usually System for backend logic, but callable by User).
    *   **Important**: Set `auth` function to run as System. Set others to be callable by the authenticated user.

### Values & Secrets
1.  Go to **Values**.
2.  Create the following values (linked to Secrets):
    *   `telegramBotToken`: Your Telegram Bot Token.
    *   `yookassaShopId`: Your Yookassa Shop ID.
    *   `yookassaSecretKey`: Your Yookassa Secret Key.

### Hosting (Frontend)
1.  Go to **Hosting**.
2.  Upload the files from the `frontend/` directory (`index.html`, `app.js`).
3.  After deployment, you will get a URL (e.g., `https://vpn-bot-xyz.mongodbstitch.com`).

## 3. Configure Telegram Bot

1.  Open `bot_miniapp.py`.
2.  Update `WEB_APP_URL` with your App Services Hosting URL (from step 2.4).
3.  Update `TOKEN` if necessary.
4.  Run the bot:
    ```bash
    pip install -r requirements.txt
    python bot_miniapp.py
    ```

## 4. Configure Frontend

1.  Open `frontend/app.js`.
2.  Update `APP_ID` with your MongoDB App ID (found in App Services dashboard).
3.  Re-upload `app.js` to Hosting if you changed it locally.

## 5. Migrate Data (Optional)

If you have existing data in `users.json`, `configs.json`, `payments.json`:
1.  Update `MONGO_URI` in `migrate_to_mongo.py` with your connection string.
2.  Run the script:
    ```bash
    python migrate_to_mongo.py
    ```

## 6. Yookassa Integration

1.  Ensure your Yookassa Shop ID and Secret Key are correct in App Services Values.
2.  The `createPayment` function generates a link. Yookassa will redirect the user back to the bot/app after payment.
3.  To handle successful payment notifications automatically, you would need to set up an HTTP Endpoint in App Services and configure Yookassa Webhooks to point to it. (This basic implementation checks status or relies on user return).

## Notes

-   **Dependencies**: Ensure `pyTelegramBotAPI`, `pymongo` are installed.
-   **Security**: The `auth` function validates the Telegram signature. Ensure your bot token is kept secret in App Services.
