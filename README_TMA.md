# Telegram Mini App (TMA) - VPN Bot Migration

This guide details how to set up the MongoDB Atlas App Services (formerly Stitch) backend and the frontend for the VPN Bot Mini App.

## 1. Project Structure

- `backend/stitch/functions/`: Contains the serverless functions for business logic.
- `frontend/`: Contains the HTML/CSS/JS for the Mini App UI.
- `bot_tma.py`: Python bot (aiogram) to launch the Mini App.

## 2. MongoDB Atlas Setup

1.  **Create a Cluster:** Sign up for MongoDB Atlas and create a free tier cluster.
2.  **Create a Database:** Name it `vpn_bot`.
3.  **Create Collections:**
    - `users`: Stores user profiles, balances, and subscriptions.
    - `configs`: Stores the VPN configuration strings/links.
    - `payments`: Stores payment history.

### Schema Design

**Collection: `users`**
```json
{
  "_id": "123456789", // Telegram User ID (String)
  "username": "johndoe",
  "first_name": "John",
  "balance": 150.0,
  "subscription_end": "2023-12-31T23:59:59Z", // ISO Date String
  "referrals_count": 5,
  "referred_by": "987654321", // ID of referrer
  "used_configs": [
    {
      "config_name": "Config 1",
      "config_link": "vless://...",
      "period": "1_month",
      "issue_date": "2023-11-01"
    }
  ]
}
```

**Collection: `configs`**
```json
{
  "_id": ObjectId("..."),
  "period": "1_month", // "1_month", "3_months", etc.
  "link": "vless://...",
  "code": "CODE123",
  "used": false,
  "assigned_to": null, // User ID when assigned
  "name": "Config_1_month_1"
}
```

**Collection: `payments`**
```json
{
  "_id": "uuid-v4",
  "user_id": "123456789",
  "amount": 100,
  "status": "pending", // "pending", "succeeded", "canceled"
  "yookassa_id": "payment_id_from_yookassa",
  "created_at": "2023-11-01T12:00:00Z"
}
```

## 3. Atlas App Services Setup

1.  **Create an App:** Go to "App Services" tab in Atlas and create a new app linked to your cluster.
2.  **Authentication:**
    - Enable **Custom Function Authentication**.
    - Create a function named `auth` (code provided in `backend/stitch/functions/auth.js`) and link it.
3.  **Functions:**
    - Import/Create all functions from `backend/stitch/functions/`.
    - Ensure dependencies: Go to "Dependencies" and add `axios` (if available) or use built-in `context.http`.
4.  **Values (Secrets):**
    - Create a Value named `botToken` (Secret) with your Telegram Bot Token.
    - Create a Value named `yookassaShopId` (Secret).
    - Create a Value named `yookassaSecretKey` (Secret).

## 4. Frontend Deployment

1.  **Hosting:** Use Atlas App Services Hosting (under "Hosting" in the sidebar) or GitHub Pages.
2.  **Upload:** Upload the contents of `frontend/` (index.html, style.css, app.js).
3.  **Config:** Update `frontend/app.js` with your **App ID** (found in App Services Dashboard).

## 5. Python Bot Setup

1.  Install dependencies: `pip install aiogram aiohttp`
2.  Run the bot: `python bot_tma.py`
3.  Ensure your bot token is set in `bot_tma.py` or environment variables.

## 6. Migration (Optional)

If you have existing data in `users.json`, you can write a script using `pymongo` to insert it into the Atlas cluster.
