# Telegram Mini App (TMA) with MongoDB Atlas App Services

This project converts the VPN Bot into a modern Telegram Mini App (Web App) using a serverless backend on MongoDB Atlas (formerly Stitch).

## Architecture

*   **Frontend:** A Single Page Application (SPA) built with HTML, Tailwind CSS, and Vanilla JS. It uses the `Realm Web SDK` to communicate directly with Atlas Functions.
*   **Backend:** Serverless Functions hosted on MongoDB Atlas App Services.
*   **Database:** MongoDB Atlas (Collections: `users`, `configs`, `payments`, `settings`).
*   **Bot:** A lightweight Python bot (`aiogram`) that launches the Mini App.

## Prerequisite Setup

### 1. MongoDB Atlas Setup
1.  Create a [MongoDB Atlas Account](https://www.mongodb.com/cloud/atlas).
2.  Create a **Project** and deploy a **Cluster** (M0 Free Tier works).
3.  Go to **App Services** tab and create a new App.
    *   Name: `VPN-Bot-App`
    *   Link to your Cluster.

### 2. Configure Database Collections
In your Cluster (Data Explorer), create a database named `vpn_bot` and the following collections:
*   `users`
*   `configs`
*   `payments`
*   `settings`

Insert a document into `settings` with `_id: "pricing"`:
```json
{
  "_id": "pricing",
  "periods": {
    "1_month": { "price": 50, "days": 30, "name": "1 Month" },
    "2_months": { "price": 90, "days": 60, "name": "2 Months" },
    "3_months": { "price": 120, "days": 90, "name": "3 Months" }
  }
}
```

### 3. Configure App Services Functions
Go to your App Services Dashboard.

#### Authentication
1.  Go to **Authentication** -> **Providers**.
2.  Enable **Custom Function Authentication**.
3.  Select "Create New Function" and name it `auth`.
4.  Copy the code from `backend/stitch/functions/auth.js` into this function.
5.  Save and Deploy.

#### Functions
Create the following functions (copy code from `backend/stitch/functions/`):
*   `getUserProfile`
*   `getConfigs`
*   `getMyConfigs`
*   `createPayment`
*   `checkPayment`
*   `buySubscription`

**Important:** Ensure all functions run as **System User** (or grant appropriate Rules/Permissions to the collections if running as Application User). For simplicity in MVP, System User bypasses Rules, but for production, configure Rules.

### 4. Configure Values & Secrets
Go to **Values** in the sidebar. Create the following:

1.  **Secret:** `yookassaSecretKey` (Value: Your YooKassa Secret Key)
2.  **Value:** `yookassaSecretKey` (Link to the secret above)
3.  **Value:** `yookassaShopId` (Value: Your Shop ID, e.g., "1172989")
4.  **Value:** `botToken` (Value: Your Telegram Bot Token)

### 5. Frontend Deployment
1.  Go to **Hosting** in the sidebar.
2.  Enable Hosting.
3.  Upload the files from the `frontend/` folder (`index.html`, `style.css`, `app.js`).
4.  **Crucial:** Note your App ID (found in the App Services UI, e.g., `vpn-bot-xyz`).
5.  Edit `frontend/app.js` and replace `REALM_APP_ID` with your actual App ID.
6.  Deploy the hosting changes.
7.  Copy the **App URL** (e.g., `https://vpn-bot-xyz.mongodbstitch.com`).

### 6. Bot Setup
1.  Open `bot_tma.py`.
2.  Update `WEB_APP_URL` with your hosted App URL.
3.  Install dependencies:
    ```bash
    pip install aiogram
    ```
4.  Run the bot:
    ```bash
    python bot_tma.py
    ```

## Usage
1.  Open your bot in Telegram.
2.  Send `/start`.
3.  Click the "Open VPN App" button.
4.  The Mini App will launch, authenticate you automatically, and show your profile.

## Admin Tasks
To add configs to the pool, use MongoDB Compass or Atlas Data Explorer to insert documents into the `configs` collection:
```json
{
  "period": "1_month",
  "link": "vless://...",
  "used": false,
  "name": "NL-1"
}
```
