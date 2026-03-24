exports = async function(paymentId) {
  const telegramId = context.user.identities[0].id;
  const db = context.services.get("mongodb-atlas").db("vpn_bot");

  const payment = await db.collection("payments").findOne({ _id: paymentId, user_id: telegramId });

  if (!payment) {
    return { success: false, message: "Payment not found or access denied." };
  }

  if (payment.status !== "pending") {
    return { success: true, status: payment.status, amount: payment.amount };
  }

  const yookassaShopId = context.values.get("YOOKASSA_SHOP_ID");
  const yookassaSecret = context.values.get("YOOKASSA_SECRET_KEY");

  // HTTP call to YooKassa
  const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: {
      "Authorization": ["Basic " + Buffer.from(`${yookassaShopId}:${yookassaSecret}`).toString('base64')]
    }
  });

  if (response.statusCode >= 400) {
    console.error("YooKassa check error: ", response.body.text());
    return { success: false, message: "Error verifying payment with provider." };
  }

  const yookassaData = EJSON.parse(response.body.text());

  if (yookassaData.status === "succeeded") {
     const amount = parseFloat(yookassaData.amount.value);

     // Atomically update balance
     await db.collection("users").updateOne(
       { telegram_id: payment.user_id },
       { $inc: { balance: amount } }
     );

     // Update payment status
     await db.collection("payments").updateOne(
       { _id: paymentId },
       { $set: { status: "confirmed" } }
     );

     return { success: true, status: "confirmed", amount: amount };
  } else if (yookassaData.status === "canceled") {
     await db.collection("payments").updateOne(
       { _id: paymentId },
       { $set: { status: "canceled" } }
     );
     return { success: true, status: "canceled", amount: 0 };
  }

  return { success: true, status: "pending", amount: payment.amount };
};