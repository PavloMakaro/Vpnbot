# Migration to Telegram Mini App with MongoDB Atlas App Services

This guide explains how to convert your existing Python bot to a Telegram Mini App hosted on MongoDB Atlas App Services.

## Prerequisites

1.  A MongoDB Atlas account.
2.  Telegram Bot Token.
3.  Yookassa Shop ID and Secret Key.

## Step 1: MongoDB Atlas Setup

1.  Log in to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2.  Create a new Cluster (Shared Tier M0 is free).
3.  Create a Database User (Username/Password) for the migration script.
4.  Allow access from anywhere (0.0.0.0/0) or your IP in Network Access.
5.  Create a Database named `vpn_bot` with collections: `users`, `configs`, `payments`.

## Step 2: App Services Setup

1.  In Atlas, go to the "App Services" tab.
2.  Create a new App (e.g., `VPNBotApp`).
3.  Link it to your Cluster.

### Authentication
1.  Go to **Authentication** > **Providers**.
2.  Enable **Custom Function Authentication**.
3.  Select the function `authTelegram` (we will create it in the next step, for now just enable it and come back later to link it, or create a placeholder function first).

### Values & Secrets
1.  Go to **Values**.
2.  Create the following Values (linked to Secrets for security):
    *   `botToken`: Your Telegram Bot Token.
    *   `yookassaShopId`: Your Yookassa Shop ID.
    *   `yookassaSecretKey`: Your Yookassa Secret Key.

### Dependencies
1.  Go to **Functions** > **Dependencies**.
2.  Add the following NPM package:
    *   `uuid` (version `latest`)

### Functions
Create the following functions in the App Services UI (copy code from `backend/stitch/functions/`):

1.  `verifyTelegramAuth`: (Private) Validates Telegram data.
2.  `authTelegram`: (Public/Auth Provider) Used for Custom Auth.
    *   *After creating this, go back to Authentication > Custom Function and select this function.*
3.  `getUserProfile`: Returns user info.
4.  `getAvailablePlans`: Returns subscription plans.
5.  `buySubscription`: Handles purchase logic.
6.  `createPayment`: Creates Yookassa payment.
7.  `yookassaWebhook`: Handles callbacks from Yookassa.
    *   **Settings**: set Authentication to "System" or "Application Auth" depending on how you call it. Since Yookassa calls it, you might need a separate HTTPS Endpoint.
    *   **HTTPS Endpoint**: Go to **HTTPS Endpoints**, create new. Route `/webhook`, Method `POST`, Function `yookassaWebhook`. **Note the URL**.

8.  `getMyConfigs`: Returns user configs.

### Hosting (Frontend)
1.  Go to **Hosting**.
2.  Enable Hosting.
3.  Upload the files from the `frontend/` directory (`index.html`, `app.js`, `style.css`).
4.  **Important**: In `frontend/app.js`, replace `const APP_ID = "vpn-bot-app-id";` with your actual App ID (found in App Services dashboard).
5.  Save your hosted URL (e.g., `https://vpn-bot-xyz.mongodbstitch.com`).

## Step 3: Migration

1.  Ensure you have `users.json`, `configs.json`, `payments.json` in the same directory as `migrate_to_mongo.py`.
2.  Install `pymongo`:
    ```bash
    pip install pymongo
    ```
3.  Get your MongoDB Connection String (Driver > Python) from Atlas.
4.  Run the migration:
    ```bash
    export MONGO_URI="mongodb+srv://user:pass@..."
    python migrate_to_mongo.py
    ```

## Step 4: Yookassa Setup

1.  In your Yookassa dashboard, set the **Notification URL** (Webhook) to the HTTPS Endpoint URL you created in App Services (e.g., `https://.../endpoint/webhook`).

## Step 5: Bot Update

1.  Edit `bot_miniapp.py`:
    *   Set `TOKEN` to your bot token.
    *   Set `WEBAPP_URL` to your App Services Hosting URL.
2.  Run the bot:
    ```bash
    python bot_miniapp.py
    ```
3.  Open your bot in Telegram and type `/start`. You should see the "Open VPN App" button.

## Directory Structure Created

*   `backend/stitch/functions/`: Source code for Atlas Functions.
*   `frontend/`: Source code for the Mini App.
*   `migrate_to_mongo.py`: Data migration script.
*   `bot_miniapp.py`: New bot interface.
