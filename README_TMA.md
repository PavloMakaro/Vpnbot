# VPN Bot - Telegram Mini App (TMA) Migration

This project converts the legacy `ai_studio_code.py` bot into a modern Telegram Mini App using MongoDB Atlas App Services (Stitch).

## Architecture

- **Frontend**: HTML/JS/CSS hosted on a static server (e.g., GitHub Pages, Atlas App Services Hosting).
- **Backend**: MongoDB Atlas App Services (Serverless Functions).
- **Database**: MongoDB Atlas.
- **Bot**: A lightweight Python bot (`bot_tma.py`) that serves the Mini App.

## Prerequisites

1.  **MongoDB Atlas Account**: Create a cluster.
2.  **Yookassa Account**: Shop ID and Secret Key.
3.  **Telegram Bot Token**: Get from @BotFather.

## Setup Instructions

### 1. Database Migration

If you have existing data in JSON files (`users.json`, `configs.json`, `payments.json`), run the migration script:

```bash
pip install pymongo
python migrate_to_mongo.py "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
```

### 2. Backend (Atlas App Services)

1.  Create a new App Service in MongoDB Atlas.
2.  **Authentication**: Enable "Custom Function Authentication".
3.  **Values**: Create the following **Values** (Secret):
    - `BOT_TOKEN`: Your Telegram Bot Token.
    - `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID.
    - `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key.
4.  **Functions**: Create the following functions (copy code from `backend/stitch/functions/`):
    - `auth`: Authentication logic. Set to "Run As: System".
    - `getProfile`: User profile. Set to "Run As: User".
    - `getConfigs`: User configs. Set to "Run As: User".
    - `buySubscription`: Purchase logic. Set to "Run As: User".
    - `createPayment`: Payment creation. Set to "Run As: User".
    - `checkPayment`: Payment checking. Set to "Run As: User".
5.  **HTTPS Endpoints** (Optional): If you want Yookassa Webhooks, create an HTTPS endpoint that calls `checkPayment`.

### 3. Frontend

1.  Edit `frontend/app.js`:
    - Replace `REALM_APP_ID` with your Atlas App ID.
2.  Host the `frontend` folder (e.g., drag and drop to Netlify, or use Atlas App Services Hosting).
3.  Get the URL (e.g., `https://my-vpn-bot.netlify.app`).

### 4. Bot Setup

1.  Edit `bot_tma.py`:
    - Set `TOKEN` to your bot token.
    - Set `WEBAPP_URL` to your hosted frontend URL.
2.  Run the bot:
    ```bash
    pip install aiogram
    python bot_tma.py
    ```
3.  In @BotFather, set the Menu Button to your Web App URL.

### 5. Admin

To add new configs to the database:

1.  Create a text file with links (one per line).
2.  Run:
    ```bash
    python admin_tool.py add_configs 1_month my_links.txt --uri "your_mongo_uri"
    ```
