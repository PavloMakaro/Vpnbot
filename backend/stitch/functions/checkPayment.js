exports = async function(paymentId) {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("User not authenticated");
  }

  const telegramId = user.id;

  const mongodb = context.services.get("mongodb-atlas");
  const paymentsCollection = mongodb.db("vpn_bot").collection("payments");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  const paymentDoc = await paymentsCollection.findOne({ _id: paymentId, user_id: telegramId });
  if (!paymentDoc) {
    throw new Error("Payment not found");
  }

  if (paymentDoc.status !== "pending") {
    return paymentDoc;
  }

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
    throw new Error("Yookassa configuration missing in Context Values");
  }

  const basicAuth = Buffer.from(`${shopId}:${secretKey}`).toString("base64");

  const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: {
      "Authorization": [`Basic ${basicAuth}`]
    }
  });

  if (response.statusCode >= 400) {
    throw new Error("Failed to get payment from Yookassa");
  }

  const yooPayment = JSON.parse(response.body.text());

  if (yooPayment.status === "succeeded") {
    // Update payment status
    await paymentsCollection.updateOne(
      { _id: paymentId },
      { $set: { status: "confirmed" } }
    );

    // Update user balance
    await usersCollection.updateOne(
      { _id: telegramId },
      { $inc: { balance: paymentDoc.amount } }
    );

    paymentDoc.status = "confirmed";
  } else if (yooPayment.status === "canceled") {
    await paymentsCollection.updateOne(
      { _id: paymentId },
      { $set: { status: "canceled" } }
    );
    paymentDoc.status = "canceled";
  }

  return paymentDoc;
};