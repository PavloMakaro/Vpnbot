exports = async function(paymentId) {
  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
    throw new Error("YooKassa credentials not configured");
  }

  const user = context.user;
  const telegramIdentity = user.identities.find(id => id.provider_type === 'custom-function');
  if (!telegramIdentity) throw new Error("User identity not found");
  const telegramId = telegramIdentity.id;

  const mongodb = context.services.get("mongodb-atlas");
  const paymentsCollection = mongodb.db("vpn_bot").collection("payments");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  const payment = await paymentsCollection.findOne({ _id: paymentId });
  if (!payment) {
    throw new Error("Payment not found");
  }

  if (payment.user_id !== telegramId) {
      throw new Error("Unauthorized access to payment");
  }

  if (payment.status === 'succeeded') {
    return { status: 'succeeded' };
  }

  // Check with YooKassa
  const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: {
      "Authorization": ["Basic " + Buffer.from(`${shopId}:${secretKey}`).toString('base64')]
    }
  });

  if (response.statusCode >= 300) {
     throw new Error(`YooKassa error: ${response.body.text()}`);
  }

  const remotePayment = JSON.parse(response.body.text());

  if (remotePayment.status !== payment.status) {
    await paymentsCollection.updateOne(
      { _id: paymentId },
      { $set: { status: remotePayment.status, updated_at: new Date() } }
    );

    if (remotePayment.status === 'succeeded' && payment.status !== 'succeeded') {
      await usersCollection.updateOne(
        { _id: payment.user_id },
        { $inc: { balance: payment.amount } }
      );
    }
  }

  return { status: remotePayment.status };
};
