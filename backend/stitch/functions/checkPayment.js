exports = async function(paymentId) {
  const user = context.user;
  if (!user || !user.identities || user.identities.length === 0) {
    throw new Error("User not authenticated properly.");
  }

  // Extract custom identity ID which is the Telegram ID
  const telegramId = user.identities[0].id;
  const SHOP_ID = context.values.get("YOOKASSA_SHOP_ID");
  const SECRET_KEY = context.values.get("YOOKASSA_SECRET_KEY");

  if (!SHOP_ID || !SECRET_KEY) {
    throw new Error("Yookassa credentials are not configured.");
  }

  const mongodb = context.services.get("mongodb-atlas");
  const paymentsCollection = mongodb.db("vpn_bot").collection("payments");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  const paymentRecord = await paymentsCollection.findOne({ payment_id: paymentId, user_id: telegramId });

  if (!paymentRecord) {
      return { success: false, message: "Payment not found or unauthorized." };
  }

  if (paymentRecord.status === 'confirmed') {
      return { success: true, message: "Payment already confirmed." };
  }

  const auth = "Basic " + Buffer.from(SHOP_ID + ":" + SECRET_KEY).toString("base64");

  const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: {
      "Authorization": [auth]
    }
  });

  if (response.statusCode >= 200 && response.statusCode < 300) {
    const paymentData = JSON.parse(response.body.text());

    if (paymentData.status === 'succeeded') {
        // Update payment status
        await paymentsCollection.updateOne(
            { payment_id: paymentId },
            { $set: { status: 'confirmed' } }
        );

        // Update user balance
        let parsedId = parseInt(telegramId);
        if (isNaN(parsedId)) {
          parsedId = telegramId;
        }

        const amount = parseFloat(paymentData.amount.value);
        await usersCollection.updateOne(
            { $or: [{ telegram_id: parsedId }, { telegram_id: telegramId }] },
            { $inc: { balance: amount } }
        );

        return { success: true, message: "Payment confirmed and balance updated." };
    } else if (paymentData.status === 'canceled') {
         await paymentsCollection.updateOne(
            { payment_id: paymentId },
            { $set: { status: 'canceled' } }
        );
        return { success: false, message: "Payment was canceled." };
    }

    return { success: false, message: "Payment is still pending." };

  } else {
    console.error(`Yookassa API Error: ${response.statusCode} - ${response.body.text()}`);
    return { success: false, message: "Failed to check payment status." };
  }
};
