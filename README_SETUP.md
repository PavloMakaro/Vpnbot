# Telegram Mini App Setup Guide (MongoDB Atlas & Stitch)

This guide explains how to deploy the Telegram Mini App using MongoDB Atlas App Services (formerly Stitch).

## Prerequisites

1.  A MongoDB Atlas account (cloud.mongodb.com).
2.  A Telegram Bot Token (from @BotFather).
3.  YooKassa Shop ID and Secret Key.
4.  Python 3.x installed (for migration and bot script).

## Step 1: MongoDB Atlas Setup

1.  Log in to MongoDB Atlas.
2.  Create a new Cluster (M0 Free Tier is sufficient).
3.  Create a Database User (e.g., `admin`) and allow Network Access (0.0.0.0/0 for testing).
4.  Get your Connection String (e.g., `mongodb+srv://admin:password@cluster0...`).

## Step 2: App Services (Stitch) Setup

1.  Go to the "App Services" tab in Atlas.
2.  Create a new App. Link it to your Cluster.
3.  Note your **App ID** (e.g., `application-0-xyz`).

### Authentication
1.  Go to **Authentication** -> **Providers**.
2.  Enable **Custom Function Authentication**.
3.  Select the function `auth` (we will create it next) as the authentication function.

### Functions
1.  Go to **Functions**.
2.  Create the following functions and paste the content from the `backend/stitch/functions/` directory:
    *   `auth`: Content of `backend/stitch/functions/auth.js`.
    *   `getProfile`: Content of `backend/stitch/functions/get_profile.js`.
    *   `getPlans`: Content of `backend/stitch/functions/get_plans.js`.
    *   `getMyConfigs`: Content of `backend/stitch/functions/get_my_configs.js`.
    *   `createPayment`: Content of `backend/stitch/functions/create_payment.js`.
    *   `buySubscription`: Content of `backend/stitch/functions/buy_subscription.js`.
    *   `yookassaWebhook`: Content of `backend/stitch/functions/yookassa_webhook.js`.
3.  **Important**: Update placeholders in the code:
    *   In `auth`: `BOT_TOKEN`.
    *   In `create_payment`: `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, return URL.

### HTTPS Endpoint (Webhook)
1.  Go to **HTTPS Endpoints**.
2.  Create a new Endpoint.
    *   Route: `/webhook`
    *   Function: `yookassaWebhook`
    *   HTTP Method: `POST`
    *   Respond with Result: Disabled (we handle response in function if needed, or leave enabled and return 200).
3.  Copy the Endpoint URL and set it in your YooKassa dashboard as the notification URL.

### Hosting (Frontend)
1.  Go to **Hosting**.
2.  Enable Hosting.
3.  Upload the files from the `frontend/` directory (`index.html`, `style.css`, `app.js`).
4.  **Important**: Before uploading, edit `frontend/app.js` and replace `APP_ID` with your actual Realm App ID.
5.  After deployment, you will get a URL (e.g., `https://application-0-xyz.mongodbstitch.com`).

## Step 3: Data Migration

1.  Ensure you have your old `users.json`, `configs.json`, `payments.json` in the root directory.
2.  Install `pymongo`:
    ```bash
    pip install pymongo
    ```
3.  Edit `migrate_to_mongo.py` and set your `MONGO_URI`.
4.  Run the script:
    ```bash
    python3 migrate_to_mongo.py
    ```

## Step 4: Run the Bot

1.  Edit `bot_miniapp.py`:
    *   Set `TOKEN` to your Bot Token.
    *   Set `APP_URL` to your deployed frontend URL (from Step 2 Hosting).
2.  Install dependencies:
    ```bash
    pip install pyTelegramBotAPI
    ```
3.  Run the bot:
    ```bash
    python3 bot_miniapp.py
    ```

## Step 5: Telegram Bot Configuration

1.  Open @BotFather.
2.  Select your bot.
3.  Go to **Bot Settings** -> **Menu Button**.
4.  Configure the menu button to open your Web App URL.
