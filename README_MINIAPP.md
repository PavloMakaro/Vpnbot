# VPN Bot Mini App Migration Guide

This guide explains how to migrate your existing VPN Telegram bot to a Telegram Mini App using MongoDB Atlas App Services (formerly Stitch).

## Prerequisites

1.  **MongoDB Atlas Account**: Create a free account at [mongodb.com](https://www.mongodb.com/cloud/atlas).
2.  **Telegram Bot Token**: You already have this.
3.  **Yookassa Credentials**: You already have these (`shopId`, `secretKey`).

## Step 1: Set up MongoDB Atlas

1.  Create a new Cluster (free tier is fine).
2.  Create a Database named `vpn_bot`.
3.  Create the following collections in `vpn_bot`:
    *   `users`
    *   `configs`
    *   `payments`
    *   `plans`
4.  Add a Database User (username/password) with read/write access to `vpn_bot`.
5.  Get your Connection String (e.g., `mongodb+srv://<user>:<password>@cluster0...`).

## Step 2: Migrate Data (Optional)

If you have existing data in `users.json`, `configs.json`, etc.:

1.  Set the environment variable `MONGO_URI`:
    ```bash
    export MONGO_URI="your_connection_string"
    ```
2.  Run the migration script:
    ```bash
    python3 migrate_to_mongo.py
    ```

## Step 3: Set up Atlas App Services (Backend)

1.  In Atlas, click on "App Services" tab and create a new App.
2.  Link it to your Cluster and the `vpn_bot` database.
3.  **Authentication**:
    *   Go to **Authentication** > **Authentication Providers**.
    *   Enable **Custom Function Authentication**.
    *   Name it `telegram-auth` (or similar).
4.  **Values & Secrets**:
    *   Go to **Values**.
    *   Create a value `telegramBotToken` (as a Secret) with your bot token.
    *   Create a value `yookassaShopId` with your Shop ID.
    *   Create a value `yookassaSecretKey` (as a Secret) with your Secret Key.
5.  **Functions**:
    *   Create the following functions (copy code from `backend/stitch/functions/`):
        *   `auth` (Set as "Private", run as System)
        *   `getUserProfile`
        *   `getPlans`
        *   `buySubscription`
        *   `createPayment`
        *   `getMyConfigs`
    *   **Important**: For `auth` function, make sure it is set as the implementation for the Custom Function Authentication provider you enabled.
    *   For other functions, ensure "Authentication" is set to "Application Authentication" (or "System" if needed, but usually App Auth is safer so `context.user` works).

## Step 4: Deploy Frontend

1.  Open `frontend/app.js`.
2.  Replace `const app = new Realm.App({ id: "vpn-bot-xxxxx" });` with your actual **App ID** (found in App Services UI).
3.  Deploy the `frontend/` folder to a static hosting provider:
    *   **Atlas App Services Hosting**: You can upload the files directly in the "Hosting" section of your App Service.
    *   **GitHub Pages**: Push the `frontend` folder to a repo and enable Pages.
    *   **Firebase Hosting**, **Vercel**, etc.
4.  Get the public URL of your deployed frontend (e.g., `https://myapp.mongodbstitch.com`).

## Step 5: Update Telegram Bot

1.  Open `bot_miniapp.py`.
2.  Update `MINI_APP_URL` with your frontend URL.
3.  Run the new bot script:
    ```bash
    python3 bot_miniapp.py
    ```
4.  Send `/start` to your bot. You should see a "Open VPN App" button.

## Step 6: Verify

1.  Open the Mini App.
2.  It should authenticate automatically.
3.  Top up balance (test mode if Yookassa supports it).
4.  Buy a subscription.
5.  Check "My Configs".

## Notes

*   **Configs**: You need to populate the `configs` collection manually or via a script. The `migrate_to_mongo.py` script handles this if you have `configs.json`.
*   **Webhooks**: For real production payments, you should set up a `webhook_payment` function and configure Yookassa to send notifications there, to handle successful payments asynchronously. The current `createPayment` function relies on the user returning to the app or manual verification, which is less robust.
