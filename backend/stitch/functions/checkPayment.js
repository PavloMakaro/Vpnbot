exports = async function(paymentId) {
  const mongodb = context.services.get("mongodb-atlas");
  const db = mongodb.db("vpn_bot");
  const payments = db.collection("payments");
  const users = db.collection("users");

  const shopId = context.values.get("yookassaShopId");
  const secretKey = context.values.get("yookassaSecretKey");

  if (!shopId || !secretKey) {
    throw new Error("Payment configuration missing");
  }

  const authString = Buffer.from(`${shopId}:${secretKey}`).toString('base64');

  // Check YooKassa API
  const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: {
      "Authorization": `Basic ${authString}`
    }
  });

  if (response.statusCode >= 400) {
     throw new Error(`YooKassa API Error: ${response.status}`);
  }

  const paymentData = JSON.parse(response.body.text());
  const status = paymentData.status; // succeeded, pending, canceled

  // Find local record
  const payment = await payments.findOne({ _id: paymentId });

  if (!payment) {
      throw new Error("Payment not found in local database");
  }

  // Idempotent update
  if (payment.status !== 'succeeded' && status === 'succeeded') {
      // Update payment status
      await payments.updateOne(
          { _id: paymentId },
          { $set: { status: 'succeeded', updated_at: new Date() } }
      );

      // Update User Balance
      const amount = parseFloat(paymentData.amount.value);
      await users.updateOne(
          { _id: payment.user_id },
          { $inc: { balance: amount } }
      );

      return { status: 'succeeded', amount: amount };
  } else if (status !== payment.status) {
       // Update other status changes (e.g. canceled)
       await payments.updateOne(
          { _id: paymentId },
          { $set: { status: status, updated_at: new Date() } }
       );
  }

  return { status: status };
};
