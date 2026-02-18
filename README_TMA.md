# Telegram Mini App (VPN Bot) - Setup Guide

This project has been converted into a Telegram Mini App using MongoDB Atlas App Services (formerly Stitch).

## Architecture
*   **Frontend**: Single Page Application (HTML/JS/Tailwind) hosted on App Services Hosting.
*   **Backend**: Serverless Functions in Atlas App Services.
*   **Database**: MongoDB Atlas.
*   **Bot**: Python script (`bot_tma.py`) to launch the Mini App.

## Deployment Steps

### 1. MongoDB Atlas Setup
1.  Create a Project and Cluster in MongoDB Atlas.
2.  Go to **App Services** tab and create a new App.
3.  Link it to your Cluster.
4.  Copy your **App ID** (e.g., `vpn_bot-xxxxx`).

### 2. Configure App Services
You need to create the functions and values in the Atlas UI or use the Realm CLI.
The code for functions is in `backend/stitch/functions/`.

**Values & Secrets:**
Create the following values in App Services (linked to Secrets for security):
*   `telegram_bot_token`: Your Telegram Bot Token.
*   `yookassa_shop_id`: Your Yookassa Shop ID.
*   `yookassa_secret_key`: Your Yookassa Secret Key.

**Functions:**
Create functions with the following names and paste the content from `backend/stitch/functions/`:
*   `auth`: Authentication (Make this **Private** but callable by script? No, this is a System function usually, or called via `Realm.Credentials.function`).
    *   *Correction*: In the frontend, we use `Realm.Credentials.function(payload)`. This maps to a specific **Custom Function Authentication** provider.
    *   Go to **Authentication** -> **Custom Function**.
    *   Select `auth` as the function.
*   `getUser`, `getConfigs`, `buySubscription`, `createPayment`: Set these as **Private** (only callable by authenticated users).
*   `yookassaWebhook`: Create an **HTTP Endpoint** (e.g., `/yookassa_webhook`) that calls this function. Method: POST.

### 3. Deploy Frontend
1.  Go to **Hosting** in App Services.
2.  Enable Hosting.
3.  Upload the files from `frontend/` (`index.html`, `style.css`, `app.js`).
4.  **Important**: Edit `frontend/app.js` and replace `STITCH_APP_ID` with your actual App ID.

### 4. Data Migration (Optional)
If you have existing data in `users.json`, `configs.json`, `payments.json`:
1.  Set `MONGO_URI` environment variable.
2.  Run `python migrate_to_mongo.py`.

### 5. Run the Bot
1.  Install dependencies: `pip install -r requirements.txt`.
2.  Set environment variables:
    ```bash
    export BOT_TOKEN="your_token"
    export MONGO_URI="mongodb+srv://..."
    export WEB_APP_URL="https://<your-app-id>.mongodbstitch.com"
    ```
3.  Run `python bot_tma.py`.
4.  Open your bot in Telegram and click "Open VPN App".

## Admin Commands
The Python bot supports basic admin commands:
*   `/add_config <period> <link>`: Add a VPN config to the database.
*   `/stats`: View user and config stats.
