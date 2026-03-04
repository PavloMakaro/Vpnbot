exports = async function(paymentId) {
  const userId = context.user.id;
  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
    throw new Error("Yookassa credentials are not configured");
  }

  const cluster = context.services.get("mongodb-atlas");
  const paymentsCollection = cluster.db("vpn_bot").collection("payments");
  const usersCollection = cluster.db("vpn_bot").collection("users");

  const paymentRecord = await paymentsCollection.findOne({ _id: paymentId, user_id: userId });
  if (!paymentRecord) {
    throw new Error("Payment record not found");
  }

  if (paymentRecord.status !== "pending") {
    return { status: paymentRecord.status };
  }

  const basicAuth = Buffer.from(`${shopId}:${secretKey}`).toString('base64');

  const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: {
      "Authorization": [`Basic ${basicAuth}`]
    }
  });

  if (response.statusCode >= 400) {
    throw new Error(`Yookassa API Error: ${response.statusCode} ${response.body.text()}`);
  }

  const paymentData = JSON.parse(response.body.text());

  if (paymentData.status === "succeeded") {
    // Payment successful
    await paymentsCollection.updateOne({ _id: paymentId }, { $set: { status: "confirmed" } });

    // Top up balance
    await usersCollection.updateOne(
      { _id: userId },
      { $inc: { balance: paymentRecord.amount } }
    );

    return { status: "succeeded" };
  } else if (paymentData.status === "canceled") {
    await paymentsCollection.updateOne({ _id: paymentId }, { $set: { status: "canceled" } });
    return { status: "canceled" };
  }

  return { status: paymentData.status }; // Still pending
};
