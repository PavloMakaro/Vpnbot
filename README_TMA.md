# Telegram Mini App VPN Bot Deployment

## Backend (Atlas App Services)
1. Create a MongoDB Atlas cluster.
2. Create an App Service linked to your cluster.
3. Deploy the functions from `backend/stitch/functions/` to your App Service.
4. Set up Custom Function Authentication pointing to `auth.js`.
5. Add Context Values:
   - `BOT_TOKEN`: Your Telegram Bot Token.
   - `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID.
   - `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key.

## Frontend
1. Update `APP_ID` in `frontend/app.js` with your Atlas App Service ID.
2. Host the `frontend/` directory on any static hosting (e.g., GitHub Pages, Vercel).

## Bot
1. Run `bot_tma.py` on your server with environment variables:
   - `BOT_TOKEN`: Your Telegram Bot Token.
   - `WEBAPP_URL`: The URL where your frontend is hosted.

## Migration
1. Set `MONGO_URI` environment variable.
2. Run `migrate_to_mongo.py` to move data from legacy JSON to MongoDB.
