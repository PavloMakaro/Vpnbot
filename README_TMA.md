# VPN Bot Mini App Deployment

This project transitions the old Telegram Bot into a modern **Telegram Mini App** using a serverless **MongoDB Atlas App Services (Stitch)** backend and an **aiogram** Python bot entry point.

## 1. MongoDB Atlas Setup
1. Create a MongoDB Atlas cluster and a database named `vpn_bot`.
2. Create three collections: `users`, `configs`, `payments`.
3. Go to the "App Services" tab and create a new App.

## 2. App Services Configuration

### Environment Variables & Context Values
In App Services, navigate to "Values" and create the following values (store as secrets where appropriate):
- `BOT_TOKEN`: Your Telegram Bot Token
- `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID
- `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key
- `MINI_APP_URL`: The URL where your frontend is hosted (e.g. `https://your-domain.github.io/vpn-bot`)

### Custom Authentication
1. Go to Authentication -> Custom Function.
2. Enable it and paste the code from `backend/stitch/functions/auth.js`.
3. This will validate Telegram's `initData` using your `BOT_TOKEN` Context Value.

### Functions
Create the following functions in App Services and paste the respective code from `backend/stitch/functions/`:
- `getProfile`
- `getConfigs`
- `buySubscription`
- `createPayment`
- `checkPayment`

## 3. Frontend Deployment
1. Host the contents of the `frontend/` directory (e.g., via GitHub Pages, Vercel, or Netlify).
2. Edit `frontend/app.js`: replace `REALM_APP_ID = "application-0-XXXXX"` with your actual Realm App ID from MongoDB Atlas.

## 4. Bot Setup (Python)
The python bot (`bot_tma.py`) serves as the entry point, providing the Menu Button and `/start` command that opens the Web App.

1. Ensure dependencies are installed:
   ```bash
   pip install aiogram
   ```
2. Set environment variables. Do **NOT** hardcode these in the script:
   ```bash
   export BOT_TOKEN="your_bot_token"
   export MINI_APP_URL="https://your-frontend-url"
   ```
3. Run the bot:
   ```bash
   python bot_tma.py
   ```

## 5. Migrating Old Data
If you have legacy JSON files (`users.json`, `configs.json`, `payments.json`), run the migration script:
```bash
export MONGO_URI="mongodb+srv://user:pass@cluster.mongodb.net"
python migrate_to_mongo.py
```

## 6. Admin Tools
Use `admin_tool.py` to bulk upload new configuration links to the database quickly.
```bash
export MONGO_URI="mongodb+srv://user:pass@cluster.mongodb.net"
python admin_tool.py
```
