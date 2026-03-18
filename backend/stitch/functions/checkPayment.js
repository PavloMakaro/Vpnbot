exports = async function(paymentId) {
  const telegramId = context.user.identities[0].id;
  if (!telegramId) {
    throw new Error("No Telegram ID found in context");
  }

  const YOOKASSA_SHOP_ID = context.values.get("YOOKASSA_SHOP_ID");
  const YOOKASSA_SECRET_KEY = context.values.get("YOOKASSA_SECRET_KEY");

  if (!YOOKASSA_SHOP_ID || !YOOKASSA_SECRET_KEY) {
    throw new Error("Yookassa credentials are not configured");
  }

  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const paymentsCollection = db.collection("payments");
  const usersCollection = db.collection("users");

  const paymentRecord = await paymentsCollection.findOne({ _id: paymentId, user_id: telegramId });

  if (!paymentRecord) {
    throw new Error("Payment record not found");
  }

  if (paymentRecord.status === "confirmed") {
    return { success: true, message: "Payment already confirmed." };
  }

  if (paymentRecord.status === "canceled") {
    return { success: false, message: "Payment was canceled." };
  }

  // Fetch from Yookassa API
  const authString = Buffer.from(`${YOOKASSA_SHOP_ID}:${YOOKASSA_SECRET_KEY}`).toString("base64");

  const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: {
      "Authorization": [`Basic ${authString}`]
    }
  });

  if (response.statusCode >= 400) {
    throw new Error("Failed to retrieve payment from Yookassa");
  }

  const yookassaData = JSON.parse(response.body.text());

  if (yookassaData.status === "succeeded") {
    // Update balance
    const user = await usersCollection.findOne({ _id: telegramId });
    const currentBalance = user.balance || 0;
    const newBalance = currentBalance + paymentRecord.amount;

    await usersCollection.updateOne(
      { _id: telegramId },
      { $set: { balance: newBalance } }
    );

    // Update payment record
    await paymentsCollection.updateOne(
      { _id: paymentId },
      { $set: { status: "confirmed" } }
    );

    return {
      success: true,
      message: `Balance topped up by ${paymentRecord.amount} ₽`,
      newBalance: newBalance
    };
  } else if (yookassaData.status === "canceled") {
    await paymentsCollection.updateOne(
      { _id: paymentId },
      { $set: { status: "canceled" } }
    );
    return {
      success: false,
      message: "Payment was canceled."
    };
  }

  // Still pending
  return {
    success: false,
    message: "Payment is still pending."
  };
};
