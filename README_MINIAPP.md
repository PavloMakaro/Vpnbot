# Telegram VPN Mini App Guide

This guide explains how to deploy the Telegram Mini App version of the VPN Bot using MongoDB Atlas App Services (formerly Stitch).

## Project Structure

*   **frontend/**: Contains the Web App code (HTML, CSS, JS). This runs inside Telegram.
*   **backend/stitch/**: Contains the JavaScript functions to be deployed to MongoDB Atlas App Services.
*   **bot_miniapp.py**: The Python bot script that serves as the entry point for users.

## Step 1: Host the Frontend

The files in the `frontend/` folder need to be hosted on a public web server with HTTPS.

**Options:**
1.  **GitHub Pages** (Recommended):
    *   Push this repo to GitHub.
    *   Go to Settings > Pages.
    *   Select the `main` branch and `/frontend` folder (if possible, or move frontend files to root of a separate branch).
    *   Get your URL (e.g., `https://yourname.github.io/repo/`).
2.  **Netlify / Vercel**:
    *   Drag and drop the `frontend/` folder to deploy.

**Important:** Update `WEB_APP_URL` in `bot_miniapp.py` with your new HTTPS URL.

## Step 2: Set Up MongoDB Atlas & App Services

1.  **Create an Account**: Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2.  **Create a Cluster**: Create a free shared cluster.
3.  **Create Database**:
    *   Go to "Browse Collections".
    *   Create a database named `vpn_bot`.
    *   Create collections: `users`, `configs`, `payments`.
4.  **Create App Service**:
    *   Go to "App Services" tab.
    *   Create a new App (e.g., "VPN Bot App").
    *   Link it to your Cluster.
5.  **Authentication**:
    *   Go to "Authentication" in the side menu.
    *   Enable **Custom JWT** (if you want to verify Telegram data securely) or **Anonymous** (for testing).
    *   *For this simplified version, the frontend mocks the calls, but in production, you should use the Realm Web SDK.*

## Step 3: Deploy Backend Functions

1.  Go to **Functions** in your App Service.
2.  Create new functions corresponding to the ones in `backend/stitch/functions.js`:
    *   `getUser`
    *   `buySubscription`
    *   `getConfigs`
3.  Copy the code from `backend/stitch/functions.js` into these functions.
4.  **Deploy** your changes in the App Services UI.

## Step 4: Configure Yookassa (Payments)

1.  Set up the **HTTPS Endpoint** in App Services for the payment webhook.
2.  Paste the `paymentWebhook` logic from `functions.js`.
3.  Configure Yookassa to send notifications to this endpoint URL.

## Step 5: Run the Bot

1.  Install dependencies (if not already):
    ```bash
    pip install pyTelegramBotAPI
    ```
2.  Update `bot_miniapp.py`:
    *   Set `TOKEN` to your bot token.
    *   Set `WEB_APP_URL` to your hosted frontend URL.
3.  Run the bot:
    ```bash
    python3 bot_miniapp.py
    ```

## Step 6: Verify

1.  Open your bot in Telegram.
2.  Send `/start`.
3.  Click the "Open App" button.
4.  The Mini App should load.

## Notes

*   **Mocking**: The current `frontend/app.js` has a `mockDB` and simulates network calls (`api` object). To connect to real MongoDB, you need to include the MongoDB Realm Web SDK in `index.html` and replace the mock `api` methods with actual `user.functions.callFunction(...)`.
*   **Security**: Ensure you validate `Telegram.WebApp.initData` on the backend to prevent spoofing.
