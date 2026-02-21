# Telegram Mini App: VPN Bot

This guide explains how to deploy the Telegram Mini App (TMA) version of the VPN Bot using MongoDB Atlas App Services.

## Prerequisites

*   MongoDB Atlas Account
*   Telegram Bot Token (from @BotFather)
*   Yookassa Shop ID and Secret Key
*   Python 3.10+
*   Node.js (optional, for local testing)

## 1. MongoDB Atlas Setup

1.  **Create a Cluster**: Log in to MongoDB Atlas and create a new cluster (M0 Free Tier works for testing).
2.  **Create an App Service**:
    *   Go to "App Services" tab.
    *   Create a new App using the "Build your own" template.
    *   Link it to your cluster.
3.  **Authentication**:
    *   Enable **Custom Function Authentication**.
    *   Create a function named `auth` and paste the content of `backend/stitch/functions/auth.js`.
    *   Set this function as the authentication logic.
    *   Alternatively, enable **Anonymous Authentication** for testing, but Custom Function is recommended for security.
4.  **Functions**:
    *   Create the following functions in the Atlas UI and paste the content from `backend/stitch/functions/`:
        *   `getUserProfile`
        *   `createPayment`
        *   `buySubscription`
        *   `getConfigs`
        *   `yookassaWebhook`
    *   Set `yookassaWebhook` to be private? No, it needs to be an **HTTPS Endpoint** (see below).
    *   Set other functions to be "Private" (callable only by authenticated users).
5.  **HTTPS Endpoint (Webhook)**:
    *   Go to "HTTPS Endpoints".
    *   Create a new endpoint:
        *   Route: `/webhook`
        *   Function: `yookassaWebhook`
        *   HTTP Method: POST
        *   Secret Name: (Optional)
    *   Note the endpoint URL. You will need to set this as the `return_url` or notification URL in Yookassa settings if applicable, or rely on `createPayment.js` setting it.
6.  **Values & Secrets**:
    *   Go to "Values".
    *   Create the following values (linked to Secrets for sensitive data):
        *   `BOT_TOKEN`: Your Telegram Bot Token.
        *   `YOOKASSA_SHOP_ID`: Your Shop ID.
        *   `YOOKASSA_SECRET_KEY`: Your Secret Key.

## 2. Frontend Deployment

1.  Open `frontend/app.js`.
2.  Replace `REALM_APP_ID` with your Atlas App ID (found in App Services dashboard).
3.  Deploy the `frontend/` folder to a static hosting provider:
    *   **GitHub Pages**: Push the code to a repo, enable Pages for `frontend/` folder.
    *   **Vercel / Netlify**: Drag and drop the folder.
4.  Copy the URL of your deployed site (e.g., `https://my-vpn-bot.vercel.app`).

## 3. Bot Setup

1.  Open `bot_tma.py`.
2.  Set environment variables or edit the file directly:
    *   `BOT_TOKEN`: Your Telegram Bot Token.
    *   `WEBAPP_URL`: The URL from Step 2.
3.  Run the bot:
    ```bash
    pip install -r requirements.txt
    python bot_tma.py
    ```
4.  Send `/start` to your bot. You should see a "Open VPN App" button.

## 4. Data Migration (Optional)

If you have existing data in `users.json`, `configs.json`, etc.:

1.  Ensure you have the connection string to your MongoDB Cluster.
2.  Run the migration script:
    ```bash
    export MONGO_URI="your_mongodb_connection_string"
    python migrate_to_mongo.py
    ```

## 5. Testing

1.  Open the Mini App in Telegram.
2.  It should log you in automatically (if Auth function is set up correctly).
3.  Try "Buy Subscription" (Mock mode is enabled by default in `frontend/app.js` line 11. Change `MOCK_MODE = false` to use real backend).
