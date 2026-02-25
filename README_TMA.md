# Telegram Mini App with MongoDB Atlas App Services

This guide explains how to deploy the Telegram Mini App (TMA) version of the VPN Bot.

## Architecture

*   **Frontend**: Single Page Application (HTML/JS/CSS) running in Telegram WebApp. Hosted on GitHub Pages or similar.
*   **Backend**: MongoDB Atlas App Services (Serverless Functions).
*   **Database**: MongoDB Atlas.
*   **Bot**: Lightweight Python bot (`bot_tma.py`) to serve the Web App.

## Prerequisites

*   MongoDB Atlas Account.
*   Telegram Bot Token (from @BotFather).
*   Yookassa Shop ID and Secret Key.
*   Python 3.10+.

## Step 1: MongoDB Atlas Setup

1.  **Create a Cluster**: Log in to MongoDB Atlas and create a new cluster (free tier works).
2.  **Create an App Service**:
    *   Go to "App Services" tab.
    *   Create a new App using the "Build your own" template.
    *   Link it to your cluster.
    *   Name it `vpn-bot` (or similar).

## Step 2: Configure App Services

### Authentication
1.  Go to **Authentication** > **Providers**.
2.  Enable **Custom Function Authentication**.
3.  Select "Create New Function" and name it `auth`.
4.  Copy the content of `backend/stitch/functions/auth.js` into this function.
5.  Save and Deploy.

### Values & Secrets
1.  Go to **Values**.
2.  Create the following **Secrets** (Values linked to secrets):
    *   `BOT_TOKEN`: Your Telegram Bot Token.
    *   `YOOKASSA_SHOP_ID`: Your Shop ID.
    *   `YOOKASSA_SECRET_KEY`: Your Secret Key.
3.  Ensure they are accessible in functions (default).

### Functions
1.  Go to **Functions**.
2.  Create the following functions and paste the content from `backend/stitch/functions/`:
    *   `getProfile` (Content of `getProfile.js`)
    *   `getConfigs` (Content of `getConfigs.js`)
    *   `buySubscription` (Content of `buySubscription.js`)
    *   `createPayment` (Content of `createPayment.js`)
    *   `checkPayment` (Content of `checkPayment.js`)
3.  **Important**: Set "Authentication" to "System" for these functions if you want to bypass rule configuration and rely on code-level checks. Alternatively, configure "Application Authentication" and set up Rules. The provided code assumes it can access collections.

### Rules (Optional/Recommended)
If running functions as "Application Authentication", configure Database Rules for `users`, `configs`, `payments` collections to allow read/write for the owner.

## Step 3: Frontend Deployment

1.  Open `frontend/app.js`.
2.  Replace `const APP_ID = "vpn-bot-xxxxx";` with your actual **App ID** from Atlas App Services (found in App Settings).
3.  Deploy the `frontend/` folder to a static host.
    *   **GitHub Pages**: Push to a repo, enable Pages for `/frontend` or root.
    *   **Netlify/Vercel**: Drag and drop the folder.
4.  Copy the deployed URL (e.g., `https://your-site.netlify.app`).

## Step 4: Bot Setup

1.  Open `bot_tma.py` or set environment variables.
2.  Create a `.env` file:
    ```
    BOT_TOKEN=your_bot_token
    WEB_APP_URL=https://your-site.netlify.app
    ```
3.  Install dependencies:
    ```bash
    pip install aiogram python-dotenv
    ```
4.  Run the bot:
    ```bash
    python3 bot_tma.py
    ```

## Step 5: Data Migration

If you have existing data in `users.json`, `configs.json`, `payments.json`:

1.  Ensure the JSON files are in the root directory.
2.  Get your MongoDB Connection String (from Atlas > Database > Connect > Drivers).
3.  Run migration:
    ```bash
    export MONGO_URI="mongodb+srv://user:pass@cluster..."
    python3 migrate_to_mongo.py
    ```

## Usage

1.  Open your bot in Telegram.
2.  Send `/start`.
3.  Click "Open VPN Store".
4.  Enjoy!
