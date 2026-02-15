# Telegram Mini App with MongoDB Atlas (Stitch)

This guide helps you convert your Python bot to a Telegram Mini App using MongoDB Atlas App Services.

## Prerequisites
1. **MongoDB Atlas Account**: [Sign up here](https://www.mongodb.com/cloud/atlas).
2. **Telegram Bot Token**: From @BotFather.
3. **Yookassa Keys**: Shop ID and Secret Key.

## Step 1: Database Setup
1. Create a **Cluster** in MongoDB Atlas (Shared Tier M0 is free).
2. Create a Database named `vpn_bot`.
3. Create Collections: `users`, `configs`, `payments`.
4. **Migration**:
   - Ensure you have `users.json`, `configs.json`, `payments.json` in the project root.
   - Install dependencies: `pip install pymongo python-dotenv`.
   - Create a `.env` file with your connection string: `MONGO_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/`.
   - Run: `python migrate_to_mongo.py`.

## Step 2: Atlas App Services (Backend)
1. Go to **App Services** tab in Atlas and create a new App.
2. Link it to your Cluster.
3. **Authentication**:
   - Enable **Custom Function Authentication**.
   - Select the function named `auth` (we will create it next).
4. **Values & Secrets**:
   - Go to **Values** in the sidebar.
   - Create the following Secrets (Value Type: Secret):
     - `BOT_TOKEN`: Your Telegram Bot Token.
     - `YOOKASSA_SHOP_ID`: Your Shop ID.
     - `YOOKASSA_SECRET_KEY`: Your Secret Key.
     - `BOT_USERNAME`: Your bot's username (without @).
     - `ADMIN_ID`: Your Telegram numeric ID (string).
   - Create Values linked to these secrets with the same names (e.g., Value Name `BOT_TOKEN` maps to Secret `BOT_TOKEN`).
5. **Functions**:
   - Go to **Functions**.
   - Create the following functions and paste the code from `backend/stitch/functions/`:
     - `auth` (Make sure to set "Authentication" to "System" or "Application Authentication" depending on needs, but usually "System" for the auth function itself).
     - `getUserProfile`
     - `getPlans`
     - `buySubscription`
     - `getMyConfigs`
     - `addConfigs`
     - `createPayment`
     - `checkPayment`
     - `getStats`
   - **Important**: For `auth`, ensure it's accessible.
6. **Rules**:
   - Set up Rules for collections if accessing directly, but since we use Functions for everything, ensure functions run as System or have proper permissions.
7. **Deploy**: Click **Review & Deploy**.

## Step 3: Frontend Setup
1. Open `frontend/app.js` and replace `const APP_ID = "vpn_bot-xxxxx";` with your actual **App ID** (found in App Services dashboard).
2. Host the `frontend` folder. You can use:
   - **GitHub Pages**: Push to a repo and enable Pages.
   - **Netlify/Vercel**: Drag and drop the folder.
   - **Atlas Hosting**: Enable Hosting in App Services and upload files.
3. Copy the URL of your hosted `index.html`.

## Step 4: Bot Setup
1. Open `.env` (or create it) and add:
   ```
   BOT_TOKEN=your_token_here
   WEB_APP_URL=https://your-hosted-frontend-url.com
   ```
2. Install dependencies: `pip install pyTelegramBotAPI python-dotenv`.
3. Run the bot: `python bot_miniapp.py`.
4. Open your bot in Telegram and type `/start`. You should see the "Open VPN App" button.

## Admin Features
- Access `https://your-hosted-frontend-url.com/admin.html` to add configs.
- Since we didn't add password protection to `admin.html` (it uses Atlas Auth), ensure your `addConfigs` function checks `ADMIN_ID` securely. (It does).
