exports = async function(paymentId) {
  const user = context.user;
  if (!user) throw new Error("Unauthorized");

  // In a real scenario, Webhook is better. But user can click "I Paid".
  // Or we just check status from DB if webhook updated it.

  const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  const payment = await paymentsCollection.findOne({ _id: paymentId });

  if (!payment) throw new Error("Payment not found");

  if (payment.status === 'succeeded') {
    return { status: 'succeeded' };
  }

  // If not succeeded in DB, check Yookassa API (Double check)
  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: {
      "Authorization": "Basic " + Buffer.from(`${shopId}:${secretKey}`).toString('base64')
    }
  });

  const responseBody = EJSON.parse(response.body.text());

  if (responseBody.status === 'succeeded' && payment.status !== 'succeeded') {
    // Update DB
    await paymentsCollection.updateOne(
      { _id: paymentId },
      { $set: { status: 'succeeded' } }
    );

    // Add Balance
    const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
    await usersCollection.updateOne(
      { _id: payment.user_id },
      { $inc: { balance: parseFloat(payment.amount) } }
    );

    return { status: 'succeeded' };
  }

  return { status: responseBody.status };
};
