# Telegram Mini App VPN Bot

## Overview
This project converts the original Telegram bot (telebot/aiogram) to a modern **Telegram Mini App** using a Single Page Application (SPA) for the frontend and MongoDB Atlas App Services (Stitch) for the backend.

## Structure

*   `frontend/`: The SPA. It uses HTML, Tailwind CSS, and the Realm Web SDK.
*   `backend/stitch/functions/`: Serverless functions hosted on MongoDB Atlas App Services.
*   `bot_tma.py`: The Aiogram v3.x bot that sends the initial link to the Mini App.
*   `migrate_to_mongo.py`: Script to migrate legacy JSON data to MongoDB.
*   `admin_tool.py`: CLI tool for uploading config links to the database.

## Deployment Instructions

### 1. MongoDB Atlas App Services

1.  Create a cluster in MongoDB Atlas.
2.  Create an App Services App.
3.  Go to **Authentication** -> **Custom Function**. Create a new Custom Function and paste the code from `backend/stitch/functions/auth.js`.
4.  Go to **Values & Secrets**. Add the following:
    *   `BOT_TOKEN`: Your Telegram Bot Token (Secret).
    *   `YOOKASSA_SHOP_ID`: Your Yookassa Shop ID (Value).
    *   `YOOKASSA_SECRET_KEY`: Your Yookassa Secret Key (Secret).
5.  Go to **Functions**. Create the remaining functions (`getProfile`, `getConfigs`, `buySubscription`, `createPayment`, `checkPayment`) and paste the code from the `backend/stitch/functions/` directory.
    *   Set the **Authentication** to "System" or "User" depending on the function requirements.
6.  **Important**: In `frontend/app.js`, replace `application-0-XXXXX` with your actual App ID from the Atlas App Services dashboard.

### 2. Frontend Hosting
Host the contents of the `frontend/` directory on any static hosting provider (e.g., GitHub Pages, Vercel, Netlify).

### 3. Telegram Bot Setup
1.  Set the `WEBAPP_URL` environment variable to the URL where your frontend is hosted.
2.  Set the `BOT_TOKEN` environment variable.
3.  Run `python bot_tma.py`.

### 4. Data Migration
To migrate your old JSON data to MongoDB, run:
```bash
MONGO_URI="mongodb+srv://..." python migrate_to_mongo.py
```