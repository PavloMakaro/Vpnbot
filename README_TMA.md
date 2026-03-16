# VPN Telegram Mini App

This repository contains the source code for a VPN bot that has been migrated from a traditional Telegram Bot architecture to a modern Telegram Mini App (TMA) powered by MongoDB Atlas App Services (Stitch).

## Architecture

* **Frontend:** A single-page application (SPA) built with vanilla HTML/JS and styled with Tailwind CSS. It communicates with the backend using the Realm Web SDK.
* **Backend:** Serverless JavaScript functions hosted on MongoDB Atlas App Services.
* **Database:** MongoDB Atlas cluster (`vpn_bot` database) containing `users`, `configs`, and `payments` collections.
* **Telegram Integration:** A lightweight Python script (`bot_tma.py`) using `aiogram` simply serves the Mini App URL to users via the `/start` command.

## Setup & Deployment

### 1. MongoDB Atlas Setup
1. Create a MongoDB Atlas cluster.
2. Create an App Service (Stitch) app linked to your cluster.
3. Enable "Custom Function Authentication".
4. Upload the JavaScript files from `backend/stitch/functions/` to your Atlas App Services functions.
5. In App Services, create the following **Values** (Secrets/Environment Variables):
   * `BOT_TOKEN`: Your Telegram Bot API token.
   * `YOOKASSA_SHOP_ID`: Your YooKassa Shop ID.
   * `YOOKASSA_SECRET_KEY`: Your YooKassa Secret Key.

### 2. Frontend Deployment
1. Open `frontend/index.html`.
2. Replace `YOUR_REALM_APP_ID` with your actual Atlas App Services App ID.
3. Host the `frontend` directory on a static web host (e.g., Vercel, Netlify, GitHub Pages, or an Nginx server).
4. Note the URL where your frontend is hosted.

### 3. Telegram Bot Setup
1. Talk to BotFather on Telegram to configure your bot.
2. Set up a "Menu Button" or configure the Mini App URL in BotFather to point to your frontend hosting URL.
3. On your server, run the Python entry point:
   ```bash
   export BOT_TOKEN="your_bot_token"
   export WEB_APP_URL="https://your-frontend-url.com"
   python bot_tma.py
   ```

## Migration

If you are migrating from the old JSON-based architecture:
1. Ensure your old `users.json`, `configs.json`, and `payments.json` are in the root directory.
2. Set your `MONGO_URI` environment variable.
3. Run `python migrate_to_mongo.py`.

## Administration

To bulk upload new VPN configurations:
```bash
python admin_tool.py <period> <link1> <link2> ...
```
Example:
```bash
python admin_tool.py 1_month vless://link1 vless://link2
```