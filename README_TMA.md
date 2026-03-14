# VPN Bot - Telegram Mini App Architecture

This project has been migrated from a legacy Python Telegram bot to a Telegram Mini App architecture, using MongoDB Atlas App Services (Stitch) as the backend and a vanilla JavaScript frontend.

## Components

1.  **Frontend (`frontend/`)**: A Single Page Application (SPA) built with HTML, Tailwind CSS, and vanilla JavaScript. It uses the Realm Web SDK to communicate with the MongoDB Atlas App Services backend.
2.  **Backend (`backend/stitch/functions/`)**: JavaScript Serverless Functions hosted on MongoDB Atlas App Services.
3.  **Bot Server (`bot_tma.py`)**: A minimal Python script using `aiogram` to serve the Web App link via the `/start` command.
4.  **Utilities**:
    *   `migrate_to_mongo.py`: Migrates data from legacy JSON files to MongoDB.
    *   `admin_tool.py`: Bulk uploads configurations to MongoDB.

## Deployment Instructions

### 1. MongoDB Atlas App Services (Backend)

1.  Create a MongoDB Atlas Cluster and a database named `vpn_bot`.
2.  Create an App Services App linked to your cluster.
3.  Set up **Custom Function Authentication**:
    *   Enable Custom Function Authentication.
    *   Create a new function and paste the contents of `backend/stitch/functions/auth.js`.
4.  Create the following Serverless Functions (paste the code from the respective files):
    *   `getProfile`
    *   `getConfigs`
    *   `buySubscription`
    *   `createPayment`
    *   `checkPayment`
    *   `checkPendingPayments`
5.  Configure **Values & Secrets**:
    *   `BOT_TOKEN`: Your Telegram Bot Token.
    *   `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID.
    *   `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key.
6.  Ensure the functions have appropriate execution roles (usually System or a custom role that allows reading/writing to the `vpn_bot` database).

### 2. Frontend

1.  Edit `frontend/app.js` and replace `YOUR_REALM_APP_ID` with your actual Realm App ID from MongoDB Atlas.
2.  Deploy the `frontend/` directory to any static web hosting service (e.g., Vercel, Netlify, GitHub Pages, or a standard web server).
3.  Note the deployed URL (e.g., `https://my-vpn-app.vercel.app`).

### 3. Telegram Bot Server

1.  Set the environment variables:
    *   `BOT_TOKEN`: Your Telegram Bot Token.
    *   `WEB_APP_URL`: The deployed URL of your frontend.
2.  Run the bot:
    ```bash
    python bot_tma.py
    ```
3.  Configure your Telegram bot via BotFather to point the Menu Button to your Web App URL, or let users click the inline button from the `/start` command.

### 4. Migration & Admin Tools

1.  Set the `MONGO_URI` environment variable.
2.  Run `migrate_to_mongo.py` to migrate existing JSON data (if any).
3.  Use `admin_tool.py` to upload new configurations:
    ```bash
    python admin_tool.py --period 1_month --file configs.txt
    ```

## Development

*   **Frontend**: You can run the frontend locally using any local web server (e.g., `python -m http.server 8000` inside the `frontend/` directory). The `app.js` contains fallback logic to mock authentication when running on `localhost`.
*   **Tests**: Run the Python unit tests with:
    ```bash
    python -m unittest test_migration.py test_admin.py
    ```
