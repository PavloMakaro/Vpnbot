# VPN Bot Telegram Mini App (TMA)

This project is a migration of the existing Telegram VPN Bot into a Telegram Mini App using MongoDB Atlas App Services (Stitch).

## Architecture

* **Frontend (`frontend/`)**: A vanilla JS Single Page Application (SPA) using Realm Web SDK to communicate with the backend. Styled with Tailwind CSS. It handles user authentication via Telegram's `initData`.
* **Backend (`backend/stitch/functions/`)**: Serverless JavaScript functions deployed to MongoDB Atlas App Services. They handle profile retrieval, configuration assignments, and Yookassa payment integration.
* **Database**: MongoDB Atlas database named `vpn_bot` with collections: `users`, `configs`, and `payments`.
* **Bot Entry Point (`bot_tma.py`)**: A simple aiogram v3 bot that serves the Mini App URL to the user via the `/start` command.

## Deployment Instructions (MongoDB Atlas App Services)

1. **Create an Atlas Cluster and App Service:**
   - Go to MongoDB Atlas, create a cluster.
   - Go to App Services, create a new App. Note the **App ID**.

2. **Configure Authentication:**
   - In App Services -> Authentication, enable **Custom Function Authentication**.
   - Select the `auth` function (from `backend/stitch/functions/auth.js`) as the custom authentication function.
   - This function validates the Telegram `initData` signature.

3. **Deploy Functions:**
   - Copy the JavaScript files from `backend/stitch/functions/` into your App Services Functions section.
   - Make sure they are named correctly (`getProfile`, `getConfigs`, `buySubscription`, `createPayment`, `checkPayment`).

4. **Configure Values & Secrets:**
   - In App Services -> Values & Secrets, add the following secrets and link them to Values:
     - `BOT_TOKEN`: Your Telegram Bot Token.
     - `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID.
     - `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key.

5. **Deploy Frontend:**
   - Update `APP_ID` in `frontend/app.js` with your actual Realm App ID.
   - Host the `frontend/` directory on any static hosting (GitHub Pages, Vercel, Netlify).

6. **Start the Bot:**
   - Set the `BOT_TOKEN` environment variable.
   - Set the `WEBAPP_URL` environment variable to point to your hosted frontend.
   - Run `python bot_tma.py`.

## Migration Tool

To migrate existing JSON data to MongoDB, run:

```bash
export MONGO_URI="mongodb+srv://<user>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority"
python migrate_to_mongo.py
```

## Admin Tool

To bulk upload new VPN configurations:

```bash
export MONGO_URI="mongodb+srv://<user>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority"
python admin_tool.py --file configs.txt --period 1_month
```