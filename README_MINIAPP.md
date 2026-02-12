# Telegram Mini App Setup Instructions

## 1. MongoDB Atlas App Services (Stitch) Setup

1.  **Create an App Service**: Create a new App Service in MongoDB Atlas linked to your cluster.
2.  **Define Values**:
    *   Create a Secret named `telegramBotToken` with your bot token.
    *   Create a Value named `telegramBotToken` linked to the secret.
    *   Create a Value named `yookassaShopId` with your Shop ID.
    *   Create a Secret named `yookassaSecretKey` with your Secret Key.
    *   Create a Value named `yookassaSecretKey` linked to the secret.
    *   Create a Value named `adminId` with your Telegram ID (as string).
3.  **Create Functions**:
    *   Copy the contents of `backend/stitch/functions/` to your App Service Functions.
    *   Ensure each function is named correctly (e.g., `auth`, `getUserProfile`, `buySubscription`, etc.).
    *   Set `auth` function to private (system) if used only for custom auth, or just ensure it's not publicly callable if not needed.
4.  **Configure Authentication**:
    *   Enable "Custom Function Authentication".
    *   Select the `auth` function as the authentication function.
5.  **Configure Hosting**:
    *   Upload the contents of `frontend/` to the App Service Hosting section.
    *   Deploy the hosting.
6.  **Environment**:
    *   Ensure dependencies `crypto` (built-in) are available.
    *   Ensure HTTP service is enabled for `createPayment` function.

## 2. Database Setup

1.  **Collections**: Ensure the following collections exist in `vpn_bot` database:
    *   `users`
    *   `configs`
    *   `payments`
    *   `plans`
2.  **Migration**:
    *   If you have existing data in JSON files, run `python3 scripts/migrate_to_mongo.py`.
    *   Set `MONGODB_URI` environment variable before running.

## 3. Bot Setup

1.  **Deploy Bot**:
    *   Run `bot_miniapp.py` on your server.
    *   Set `BOT_TOKEN` and `WEB_APP_URL` environment variables.
2.  **Menu Button**:
    *   The bot will automatically set the menu button to launch the Mini App on `/start`.

## 4. Payment Webhook

1.  **Create Endpoint**:
    *   In Atlas App Services, create an HTTPS Endpoint.
    *   Route: `/webhook/yookassa`
    *   Function: `paymentWebhook`
    *   HTTP Method: POST
2.  **Yookassa Settings**:
    *   Set the Notification URL in Yookassa to your endpoint URL.
