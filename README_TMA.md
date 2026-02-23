# Telegram Mini App VPN Bot (MongoDB Atlas)

This project converts the legacy file-based VPN bot into a scalable Telegram Mini App using MongoDB Atlas App Services (formerly Stitch).

## Architecture

- **Frontend**: Single-page application (HTML/JS/Tailwind) running in Telegram WebApp.
- **Backend**: Serverless Functions on MongoDB Atlas App Services.
- **Database**: MongoDB Atlas (`vpn_bot` database).
- **Bot**: Lightweight Python bot (`aiogram`) to launch the Mini App.

## Prerequisites

1.  **MongoDB Atlas Account**: [Sign up here](https://www.mongodb.com/cloud/atlas/register).
2.  **Telegram Bot Token**: From [@BotFather](https://t.me/BotFather).
3.  **YooKassa Shop ID & Secret Key**: For payments.

## Setup Instructions

### 1. MongoDB Atlas Setup

1.  Create a new Cluster (M0 Sandbox is fine for testing).
2.  Go to **App Services** tab and create a new App.
3.  Link the App to your Cluster.

### 2. Configure Authentication

1.  In App Services, go to **Authentication**.
2.  Enable **Custom Function Authentication**.
3.  Select the function `auth` (you will create it in the next step) as the authentication function.
4.  Save and Deploy.

### 3. Deploy Backend Functions

1.  Go to **Functions**.
2.  Create the following functions and paste the content from `backend/stitch/functions/`:
    *   `auth` (Authentication logic)
    *   `getUser`
    *   `getConfigs`
    *   `getUserConfigs`
    *   `createPayment`
    *   `checkPayment`
    *   `buySubscription`
    *   `yookassaWebhook`
3.  **Important**: For `auth` function, ensure "Private" is unchecked if needed, but usually Custom Auth function is special. For other functions, set "Authentication" to "Application Authentication" (or "System" if they need elevated privileges, but verify `context.user` usage).
    *   Actually, `auth` is run by System.
    *   `yookassaWebhook` should be run by System (as it's an external webhook).
    *   All other functions (`getUser`, etc.) should be run as **User** (Application Authentication) so `context.user` is populated.

### 4. Configure Secrets (Values)

1.  Go to **Values**.
2.  Create the following values (linked to Secrets for security):
    *   `BOT_TOKEN`: Your Telegram Bot Token.
    *   `YOOKASSA_SHOP_ID`: Your Shop ID.
    *   `YOOKASSA_SECRET_KEY`: Your Secret Key.

### 5. Configure Webhook

1.  Go to **HTTPS Endpoints**.
2.  Create a new endpoint:
    *   **Route**: `/webhook/yookassa`
    *   **Method**: `POST`
    *   **Function**: `yookassaWebhook`
    *   **Respond with Result**: Off (we handle response in function).
3.  Copy the Endpoint URL and set it in your YooKassa settings for notifications.

### 6. Deploy Frontend

1.  Go to **Hosting** in App Services.
2.  Enable Hosting.
3.  Upload all files from the `frontend/` directory (`index.html`, `styles.css`, `app.js`).
4.  **Important**: In `frontend/app.js`, update the `APP_ID` variable with your App ID (found in App Services dashboard, e.g., `application-0-xxxxx`).
5.  Deploy changes.
6.  Note the **App ID** and **Hosting URL**.

### 7. Run the Bot

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Set environment variables:
    ```bash
    export BOT_TOKEN="your_bot_token"
    export WEBAPP_URL="https://<your-app-id>.mongodbstitch.com"
    ```
3.  Run the bot:
    ```bash
    python bot_tma.py
    ```

### 8. Migrate Data (Optional)

If you have existing `users.json`, `configs.json`, and `payments.json`:

1.  Set `MONGO_URI`:
    ```bash
    export MONGO_URI="mongodb+srv://<user>:<password>@cluster0.mongodb.net"
    ```
2.  Run migration:
    ```bash
    python migrate_to_mongo.py
    ```

## Notes

- **Payment Callback**: Ensure the `yookassaWebhook` is reachable by YooKassa.
- **Security**: Never commit secrets to git. use Environment Variables and Atlas Secrets.
