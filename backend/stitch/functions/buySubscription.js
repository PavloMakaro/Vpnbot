exports = async function(periodKey) {
    const userId = context.user.id;
    if (!userId) {
        throw new Error("User is not authenticated.");
    }

    const SUBSCRIPTION_PERIODS = {
        '1_month': { price: 50, days: 30 },
        '2_months': { price: 90, days: 60 },
        '3_months': { price: 120, days: 90 }
    };

    if (!SUBSCRIPTION_PERIODS[periodKey]) {
        throw new Error("Invalid subscription period.");
    }

    const amount = SUBSCRIPTION_PERIODS[periodKey].price;
    const addDays = SUBSCRIPTION_PERIODS[periodKey].days;

    const db = context.services.get("mongodb-atlas").db("vpn_bot_db");
    const usersCollection = db.collection("users");
    const configsCollection = db.collection("configs");

    // 1. Fetch user to check balance
    const userDoc = await usersCollection.findOne({ _id: userId });
    if (!userDoc) {
        throw new Error("User not found.");
    }

    const currentBalance = userDoc.balance || 0;
    if (currentBalance < amount) {
        return { success: false, message: `Недостаточно средств. Ваш баланс: ${currentBalance} ₽. Требуется: ${amount} ₽.` };
    }

    // 2. Atomically reserve a config
    const configDoc = await configsCollection.findOneAndUpdate(
        { period: periodKey, used: false },
        { $set: { used: true } },
        { returnNewDocument: true } // Return the updated document
    );

    if (!configDoc) {
        return { success: false, message: "Нет доступных конфигов для этого периода. Обратитесь в поддержку." };
    }

    // 3. Deduct balance and calculate new end date
    let newEndDate = new Date();
    if (userDoc.subscription_end_date) {
        const currentEnd = new Date(userDoc.subscription_end_date);
        if (currentEnd > newEndDate) {
            newEndDate = currentEnd;
        }
    }
    newEndDate.setDate(newEndDate.getDate() + addDays);

    // 4. Update user profile
    const usedConfigEntry = {
        config_name: configDoc.name,
        config_link: configDoc.link,
        config_code: configDoc.code,
        period: periodKey,
        issue_date: new Date().toISOString().replace('T', ' ').substring(0, 19),
        user_name: `${userDoc.first_name} (@${userDoc.username})`
    };

    await usersCollection.updateOne(
        { _id: userId },
        {
            $inc: { balance: -amount },
            $set: {
                subscription_end_date: newEndDate,
                subscription_end: newEndDate.toISOString().replace('T', ' ').substring(0, 19)
            },
            $push: { used_configs: usedConfigEntry }
        }
    );

    // 5. Return success and the config
    const day = newEndDate.getDate().toString().padStart(2, '0');
    const month = (newEndDate.getMonth() + 1).toString().padStart(2, '0');
    const year = newEndDate.getFullYear();
    const formattedDate = `${day}.${month}.${year}`;

    return {
        success: true,
        message: `✅ Подписка успешно куплена!\nСписано: ${amount} ₽\nОстаток: ${currentBalance - amount} ₽\nАктивна до: ${formattedDate}`,
        config: configDoc
    };
};