# Setup Guide for Telegram Mini App Migration

This guide explains how to deploy the Telegram Mini App using MongoDB Atlas App Services (formerly Stitch) and migrate your existing data.

## Prerequisites

1.  A MongoDB Atlas account.
2.  Your Telegram Bot Token.
3.  YooKassa Shop ID and Secret Key.
4.  Python 3 installed.

## Step 1: MongoDB Atlas Setup

1.  **Create a Cluster**: Log in to MongoDB Atlas and create a new cluster (Shared Tier M0 is fine for starting).
2.  **Create Database**: In the "Collections" tab, create a new database named `vpn_bot`.
3.  **Create Collections**: Create the following collections inside `vpn_bot`:
    *   `users`
    *   `configs`
    *   `payments`

## Step 2: Atlas App Services (Stitch) Setup

1.  **Create App**: Go to the "App Services" tab in Atlas and create a new application. Link it to your cluster.
2.  **Authentication**:
    *   Go to **Authentication** > **Providers**.
    *   Enable **Custom Function Authentication**.
    *   Select "Create New Function" and name it `auth`.
    *   Copy the code from `backend/stitch/functions/auth.js` into this function.
    *   Save and Deploy.
3.  **Values (Secrets)**:
    *   Go to **Values**.
    *   Create the following values (as "Secret"):
        *   `telegram_bot_token`: Your Telegram Bot Token.
        *   `yookassa_shop_id`: Your YooKassa Shop ID.
        *   `yookassa_secret_key`: Your YooKassa Secret Key.
    *   Link them to the `auth` function or make them global.
4.  **Functions**:
    *   Go to **Functions**.
    *   Create the following functions and paste the code from `backend/stitch/functions/`:
        *   `getProfile` -> `get_profile.js`
        *   `getPlans` -> `get_plans.js`
        *   `createPayment` -> `create_payment.js`
        *   `buySubscription` -> `buy_subscription.js`
        *   `getMyConfigs` -> `get_my_configs.js`
    *   **Settings**: Ensure "Authentication" is set to "System" or "Application Authentication" depending on needs, but generally "System" is easiest for internal logic, while callable functions should be "Application Authentication" (the default for user-called functions).
    *   **Important**: Set `createPayment`, `buySubscription`, `getProfile`, `getPlans`, `getMyConfigs` to be **Private** (false) if you only call them via the SDK. Actually, for client SDK access, you don't need to make them "System" functions. The client calls them as `user.functions.functionName()`.
5.  **HTTPS Endpoints (Webhooks)**:
    *   Go to **HTTPS Endpoints**.
    *   Create a new endpoint.
    *   Route: `/yookassa_webhook`.
    *   Function: Create new function `yookassaWebhook` and paste code from `yookassa_webhook.js`.
    *   Authentication: **No Authentication** (YooKassa sends requests without user session).
    *   Copy the Endpoint URL and set it in your YooKassa dashboard as the notification URL.
6.  **Hosting**:
    *   Go to **Hosting**.
    *   Enable Hosting.
    *   Upload the files from the `frontend/` directory (`index.html`, `style.css`, `app.js`).
    *   After deployment, you will get a URL (e.g., `https://<app-id>.mongodbstitch.com/`). This is your **Web App URL**.

## Step 3: Configure Frontend

1.  Open `frontend/app.js` locally.
2.  Find the line `const APP_ID = "vpn-bot-app-id";`.
3.  Replace `"vpn-bot-app-id"` with your actual Atlas App ID (found in the App Services dashboard).
4.  Re-upload `app.js` to Hosting if you modified it locally.

## Step 4: Data Migration

1.  Install dependencies:
    ```bash
    pip install -r requirements_miniapp.txt
    ```
2.  Set your MongoDB Connection String:
    ```bash
    export MONGO_URI="mongodb+srv://<user>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority"
    ```
3.  Ensure your `users.json`, `configs.json`, and `payments.json` are in the same directory.
4.  Run the migration script:
    ```bash
    python3 migrate_to_mongo.py
    ```

## Step 5: Run the Bot

1.  Open `bot_miniapp.py`.
2.  Update `TOKEN` and `WEB_APP_URL` with your values (or set them as environment variables).
3.  Run the bot:
    ```bash
    python3 bot_miniapp.py
    ```
4.  Open your bot in Telegram and send `/start`. Click the button to open your Mini App!

## Troubleshooting

-   **"Invalid initData signature"**: Ensure your `telegram_bot_token` secret in Atlas is correct.
-   **"Failed to create payment"**: Check your YooKassa credentials in Atlas Values.
-   **CORS Errors**: If testing locally, you might run into CORS. Using the hosted version usually avoids this.
