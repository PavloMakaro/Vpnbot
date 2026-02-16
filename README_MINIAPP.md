# 🚀 VPN Mini App Setup Guide

Это руководство поможет вам развернуть Telegram Mini App для продажи VPN конфигов, используя MongoDB Atlas (Stitch) и Yookassa.

## 1. MongoDB Atlas Setup

1.  Создайте аккаунт на [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2.  Создайте новый проект и бесплатный кластер (M0 Sandbox).
3.  Перейдите в **App Services** (вкладка сверху) и создайте новое приложение.
    *   Name: `vpn-bot`
    *   Link to Database: Выберите ваш кластер.
4.  В разделе **Data Access > Rules**:
    *   Создайте коллекцию `users` в базе `vpn_bot`. Настройте права: `readAndWriteAll` (для начала).
    *   Создайте коллекцию `configs`.
    *   Создайте коллекцию `payments`.

## 2. Настройка Backend (Functions)

1.  Перейдите в раздел **Functions**.
2.  Создайте следующие функции и скопируйте код из папки `backend/stitch/functions/`:
    *   `auth`: Настройки Authentication: **System**.
    *   `getUser`: Настройки Authentication: **Application Authentication**.
    *   `createPayment`: Настройки Authentication: **Application Authentication**.
    *   `buySubscription`: Настройки Authentication: **Application Authentication**.
    *   `yookassaWebhook`: Настройки Authentication: **System**.

3.  Для `yookassaWebhook`:
    *   После создания перейдите в **HTTPS Endpoints**.
    *   Создайте новый Endpoint.
    *   Route: `/webhook`
    *   Function: `yookassaWebhook`
    *   HTTP Method: `POST`
    *   Saves response: No.
    *   **Скопируйте URL** этого вебхука. Используйте его для настройки уведомлений в ЮKassa.

## 3. Настройка Authentication

1.  Перейдите в раздел **Authentication**.
2.  Включите провайдер **Custom Function Authentication**.
3.  В поле "Select a Function" выберите функцию `auth`.
4.  Нажмите Save и Deploy.

## 4. Настройка Secrets (Values)

1.  Перейдите в раздел **Values**.
2.  Создайте следующие значения (Secret):
    *   `BOT_TOKEN`: Токен вашего Telegram бота.
    *   `YOOKASSA_SHOP_ID`: ID магазина ЮKassa.
    *   `YOOKASSA_SECRET_KEY`: Секретный ключ API ЮKassa.

## 5. Настройка Frontend

1.  Откройте файл `frontend/app.js`.
2.  Найдите строку `const REALM_APP_ID = "vpn-bot-xxxxx";`.
3.  Замените `vpn-bot-xxxxx` на ваш **App ID** (можно найти в панели Atlas App Services сверху слева).

## 6. Деплой Frontend (Hosting)

1.  В панели App Services перейдите в **Hosting**.
2.  Включите хостинг.
3.  Нажмите **Upload Files** и загрузите все файлы из папки `frontend/` (`index.html`, `app.js` и др.).
4.  Нажмите **Deploy** (синяя кнопка сверху).
5.  Скопируйте URL вашего хостинга.

## 7. Настройка Бота

1.  Откройте `bot_miniapp.py`.
2.  Вставьте ваш `BOT_TOKEN`.
3.  Вставьте ваш URL хостинга в `WEB_APP_URL`.
4.  Запустите бота:
    ```bash
    python3 bot_miniapp.py
    ```

## 8. Миграция Данных (Опционально)

1.  Установите зависимости: `pip install pymongo`
2.  Получите строку подключения (Connection String) в Atlas.
3.  Запустите миграцию:
    ```bash
    export MONGO_URI="ваша_строка_подключения"
    python3 migrate_to_mongo.py
    ```

## Готово!
Откройте бота в Telegram, нажмите `/start` и кнопку "Открыть VPN App".
