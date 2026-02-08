# VPN Telegram Mini App Setup Guide

This guide explains how to deploy the VPN Bot as a Telegram Mini App using MongoDB Atlas App Services (formerly Stitch).

## 1. MongoDB Atlas Setup

1.  Create a [MongoDB Atlas Account](https://www.mongodb.com/cloud/atlas/register).
2.  Create a new Cluster (Free Tier M0 is fine).
3.  Create a Database User and allow Network Access (0.0.0.0/0 for simplicity, or your IP).
4.  Get your **Connection String** (needed for migration script).

## 2. App Services (Stitch) Setup

1.  In Atlas, go to **App Services** tab and create a new App.
2.  Link it to your Cluster.
3.  Note your **App ID**.

### Authentication
1.  Go to **Authentication** -> **Authentication Providers**.
2.  Enable **Custom Function Authentication**.
3.  Create a new Function named `auth` for authentication.
4.  Copy the code from `backend/stitch/functions/auth.js` into this function.
5.  Save and Deploy.

### Values & Secrets
1.  Go to **Values**.
2.  Create the following values (as Secrets where appropriate):
    -   `botToken`: Your Telegram Bot Token.
    -   `yookassaShopId`: Your Yookassa Shop ID.
    -   `yookassaSecretKey`: Your Yookassa Secret Key.

### Functions
1.  Go to **Functions**.
2.  Create the following functions and paste the code from `backend/stitch/functions/`:
    -   `getUser` (`getUser.js`)
    -   `topupBalance` (`topupBalance.js`)
    -   `buySubscription` (`buySubscription.js`)
    -   `getConfigs` (`getConfigs.js`)
    -   `webhookYookassa` (`webhookYookassa.js`)
3.  **Important**: Ensure functions run as System User or have appropriate collection permissions. Go to "Rules" -> Select collection -> Read/Write for "default" role if needed, or set Function to "System" execution.
    -   For `getUser`, `buySubscription`, `topupBalance`, `getConfigs`: Set "Run As" to "System" (easiest) or configure advanced rules.

### HTTPS Endpoints (Webhooks)
1.  Go to **HTTPS Endpoints**.
2.  Create a new Endpoint.
    -   Route: `/webhook`
    -   HTTP Method: `POST`
    -   Function: `webhookYookassa`
    -   Respond With Result: On
3.  Copy the Endpoint URL. This is your Yookassa Webhook URL.

## 3. Database Migration

1.  Ensure you have your old `users.json`, `configs.json`, `payments.json` in the root folder.
2.  Install dependencies: `pip install pymongo`.
3.  Set your MongoDB URI:
    ```bash
    export MONGODB_URI="mongodb+srv://<user>:<password>@cluster..."
    ```
4.  Run the migration script:
    ```bash
    python migrate_to_mongo.py
    ```

## 4. Frontend Deployment

1.  Open `frontend/app.js` and replace `const APP_ID = "vnp-bot-app-id";` with your actual Stitch App ID.
2.  In Atlas App Services, go to **Hosting**.
3.  Enable Hosting.
4.  Upload the files from the `frontend/` folder (`index.html`, `style.css`, `app.js`).
5.  Once deployed, copy the **Hosting URL** (e.g., `https://<app-id>.mongodbstitch.com`).

## 5. Bot Update

1.  Open `bot_miniapp.py`.
2.  Replace `WEB_APP_URL` with your Hosting URL.
3.  Replace `TOKEN` if needed.
4.  Run the bot:
    ```bash
    python bot_miniapp.py
    ```
5.  Open your bot in Telegram and send `/start`. You should see the "Open VPN App" button.

## 6. Yookassa Setup

1.  In your Yookassa dashboard, set the **Notification URL** (Webhook) to your Stitch HTTPS Endpoint URL (`.../webhook`).
2.  Enable `payment.succeeded` event.
