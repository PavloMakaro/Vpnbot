# Telegram Mini App VPN Bot Architecture

This project has been restructured from a legacy Python Telegram bot to a scalable Telegram Mini App utilizing a Single Page Application (SPA) frontend and a serverless backend hosted on **MongoDB Atlas App Services (Stitch)**.

## Project Structure

- `frontend/`: Contains the vanilla HTML/JS Mini App frontend. Uses Tailwind CSS for styling and Realm Web SDK for backend communication.
- `backend/stitch/functions/`: Contains the JavaScript functions deployed to Atlas App Services.
- `bot_tma.py`: A lightweight Python script using `aiogram` v3.x to serve the Telegram Web App link via the `/start` command.
- `migrate_to_mongo.py`: Data migration script to transfer existing data from `users.json`, `configs.json`, and `payments.json` to MongoDB.
- `admin_tool.py`: Script to bulk-upload new VPN configurations to the MongoDB `configs` collection.

## Deployment Instructions

### 1. MongoDB Atlas App Services Setup
1. Create a MongoDB Cluster on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. Create a Database named `vpn_bot` with collections: `users`, `configs`, `payments`.
3. Create an **App Services** App linked to this cluster.
4. **Authentication**: Enable **Custom Function Authentication**.
   - Create a new function and paste the contents of `backend/stitch/functions/auth.js`.
5. **Context Values**: Go to "Values" in the App Services UI and add the following secrets:
   - `BOT_TOKEN`: Your Telegram Bot Token.
   - `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID.
   - `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key.
6. **Functions**: Create functions in the Atlas UI and copy the code from the files in `backend/stitch/functions/`. Map them to the currently authenticated user context (`currentUser.functions`).
   - `getProfile`
   - `getConfigs`
   - `buySubscription`
   - `createPayment`
   - `checkPayment`
   - `checkPendingPayments`

### 2. Frontend Deployment
1. Replace the placeholder `APP_ID` in `frontend/app.js` with your actual Atlas App ID.
2. Host the contents of the `frontend/` directory on a static web host (e.g., GitHub Pages, Cloudflare Pages, Vercel).
3. Update `WEB_APP_URL` in your `.env` file (for `bot_tma.py`) or in your BotFather settings to point to your hosted frontend URL.

### 3. Python Bot (Entry Point)
1. Install dependencies: `pip install -r requirements.txt`.
2. Create a `.env` file containing:
   ```
   BOT_TOKEN=your_bot_token
   WEB_APP_URL=https://your-hosted-frontend-url.com
   ```
3. Run `python bot_tma.py`.

### 4. Admin and Migration Scripts
To migrate legacy data:
```bash
python migrate_to_mongo.py --uri "your_mongodb_connection_string"
```

To upload new VPN configs in bulk (create a text file with one config link per line):
```bash
python admin_tool.py --uri "your_mongodb_connection_string" --period "1_month" --file "configs.txt"
```