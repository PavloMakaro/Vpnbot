# Telegram Mini App with MongoDB Atlas App Services

This project converts the legacy file-based bot into a Telegram Mini App powered by MongoDB Atlas App Services (formerly Stitch).

## Architecture

*   **Frontend**: Single Page Application (SPA) using vanilla JS and Tailwind CSS.
*   **Backend**: Serverless Functions on MongoDB Atlas App Services.
*   **Database**: MongoDB Atlas.
*   **Bot**: Python `aiogram` bot serving the Mini App.

## Setup Instructions

### 1. MongoDB Atlas Setup

1.  Create a MongoDB Atlas account and a cluster.
2.  Create a new App Services App.
3.  Link it to your cluster.
4.  Create a database named `vpn_bot` and collections: `users`, `configs`, `payments`.

### 2. Configure App Services

1.  **Authentication**:
    *   Enable "Custom Function Authentication".
    *   Select the `auth` function (upload `backend/stitch/functions/auth.js` first).
2.  **Values (Environment Variables)**:
    *   Create the following Context Values (Secrets):
        *   `BOT_TOKEN`: Your Telegram Bot Token.
        *   `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID.
        *   `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key.
3.  **Functions**:
    *   Create/Upload the functions from `backend/stitch/functions/`:
        *   `auth` (Authentication Function)
        *   `getProfile`
        *   `getConfigs`
        *   `buySubscription`
        *   `createPayment`
        *   `checkPayment`
    *   **Important**: Set "Run As System" or ensure appropriate rules for `buySubscription`, `createPayment`, `checkPayment` if they access collections directly. For `getProfile` and `getConfigs`, "Run As User" is fine if you set up Rules.
    *   **Database Rules**:
        *   `users`: Owner can read/write their own document (`{ "_id": "%%user.id" }`). System can read/write all.
        *   `configs`: Users can read `{ "used": false }` (or via function only). System can read/write all.
        *   `payments`: Users can read own. System can read/write all.
        *   *Simpler Approach*: Use "System" context in functions and disable direct client access (Rules: Read/Write false for everyone), forcing all access through Functions.

### 3. Frontend Deployment

1.  Update `frontend/app.js`:
    *   Replace `YOUR_REALM_APP_ID` with your actual App ID (found in App Services UI).
2.  Host the `frontend/` folder. You can use:
    *   MongoDB App Services Hosting.
    *   GitHub Pages.
    *   Vercel/Netlify.
3.  Note the HTTPS URL (e.g., `https://myapp.mongodbstitch.com`).

### 4. Bot Setup

1.  Update `bot_tma.py` (or set env var):
    *   `WEB_APP_URL`: The URL from Step 3.
    *   `BOT_TOKEN`: Your Telegram Bot Token.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the bot:
    ```bash
    python bot_tma.py
    ```

### 5. Data Migration

If you have existing data in JSON files:

1.  Ensure `users.json`, `configs.json`, `payments.json` are in the root directory.
2.  Set `MONGO_URI` environment variable.
3.  Run migration:
    ```bash
    export MONGO_URI="your_mongodb_connection_string"
    python migrate_to_mongo.py
    ```

## Usage

1.  Open the bot in Telegram.
2.  Send `/start`.
3.  Click "Open VPN App".
4.  You should be logged in automatically and see your profile.
