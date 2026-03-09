# VPN Bot - Telegram Mini App (TMA)

This repository contains the source code for a Telegram Mini App VPN Bot, migrating from a legacy Python polling bot to a serverless architecture using MongoDB Atlas App Services (Stitch).

## Architecture

*   **Frontend**: Vanilla HTML/JS with Tailwind CSS and Realm Web SDK (`frontend/`). Hosted anywhere (e.g., GitHub Pages, Netlify).
*   **Backend**: MongoDB Atlas App Services Custom Functions (`backend/stitch/functions/`). Serverless execution, interacting directly with MongoDB.
*   **Database**: MongoDB Atlas. Database `vpn_bot` with collections `users`, `configs`, and `payments`.
*   **Entry Point**: A lightweight Python aiogram bot (`bot_tma.py`) to serve the Web App link via the `/start` command.

## Deployment Instructions

### 1. MongoDB Atlas Setup
1. Create a MongoDB Atlas cluster.
2. Create a Database named `vpn_bot`.
3. Create an App in App Services.
4. Go to **Authentication** -> **Custom Function** and link it to the `auth.js` function.
5. Create HTTP Endpoints or use the Web SDK (Realm) to expose functions:
   - `getProfile`
   - `getConfigs`
   - `buySubscription`
   - `createPayment`
   - `checkPayment`
6. Set Context Values (Environment Variables) in App Services:
   - `YOOKASSA_SHOP_ID`
   - `YOOKASSA_SECRET_KEY`

### 2. Frontend Setup
1. Edit `frontend/app.js` and replace `APP_ID` with your actual Realm App ID from MongoDB Atlas.
2. Host the `frontend` directory on a static hosting provider (e.g., Netlify, Vercel, GitHub Pages) with HTTPS.

### 3. Telegram Bot Setup
1. Talk to BotFather and set the Web App URL for your bot to point to your hosted frontend URL.
2. Host `bot_tma.py` on any server or platform (e.g., Heroku, VPS).
3. Set the `BOT_TOKEN` environment variable.

### Data Migration
If you are migrating from the old JSON file structure:
1. Ensure `users.json`, `configs.json`, and `payments.json` are in the same directory as the script.
2. Set `MONGO_URI` environment variable.
3. Run `python migrate_to_mongo.py`.

### Admin Tools
To bulk upload configurations:
1. Create a text file with one config link per line.
2. Run `python admin_tool.py <path_to_file> <period_key>`.
   Example: `python admin_tool.py new_configs.txt 1_month`