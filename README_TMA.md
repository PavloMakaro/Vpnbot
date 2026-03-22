# VPN Bot Telegram Mini App (TMA)

This repository contains the source code for the VPN Bot, migrated to a Telegram Mini App architecture using MongoDB Atlas App Services (Stitch).

## Architecture
- **Backend**: Serverless functions hosted on MongoDB Atlas App Services (`backend/stitch/functions`).
- **Database**: MongoDB Atlas Cluster.
- **Frontend**: Vanilla JavaScript Single Page Application (SPA) using Tailwind CSS and Realm Web SDK (`frontend/`).
- **Bot Entry Point**: Python bot using `aiogram` v3 to serve the Web App (`bot_tma.py`).

## Deployment Instructions (MongoDB Atlas App Services)

1. **Create an Atlas Cluster**:
   - Log in to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
   - Create a new project and cluster.
   - Create a database named `vpn_bot`.

2. **Create an App Service**:
   - Navigate to the "App Services" tab.
   - Click "Create a New App".
   - Select the cluster you created as the data source.

3. **Configure Authentication**:
   - Go to "Authentication" -> "Authentication Providers".
   - Enable "Custom Function Authentication".
   - Name the function `auth`.
   - Paste the contents of `backend/stitch/functions/auth.js` into the function body.

4. **Add Context Values**:
   - Go to "Values" -> "Create a Value".
   - Add the following secrets (type: Secret):
     - `BOT_TOKEN`: Your Telegram Bot Token.
     - `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID.
     - `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key.

5. **Create Functions**:
   - Go to "Functions" -> "Create a Function".
   - Create the following functions and paste the corresponding code from `backend/stitch/functions/`:
     - `getProfile`
     - `getConfigs`
     - `buySubscription`
     - `createPayment`
     - `checkPayment`
     - `checkPendingPayments`

6. **Deploy Frontend**:
   - Update the `app.id` in `frontend/app.js` with your actual Atlas App ID.
   - Host the `frontend/` directory on a platform like GitHub Pages, Vercel, or Netlify.
   - Ensure the hosted URL supports HTTPS.

7. **Configure Telegram Bot**:
   - Set the environment variables for your Python environment:
     - `BOT_TOKEN`: Your Telegram Bot Token.
     - `WEB_APP_URL`: The HTTPS URL where your frontend is hosted.
   - Run `python bot_tma.py` to start the bot.

8. **Migrate Data**:
   - Ensure you have a valid `MONGO_URI` environment variable pointing to your Atlas cluster.
   - Run `python migrate_to_mongo.py` to migrate data from the old JSON files.

## Administration
- Use `admin_tool.py` to bulk upload new configurations to the database.
- Example: `python admin_tool.py --upload configs.txt --period 1_month`

## Testing
- Unit tests for Python scripts: `python -m unittest test_migration.py test_admin.py`
