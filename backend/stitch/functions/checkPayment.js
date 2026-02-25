exports = async function(paymentId) {
  // Check payment status and credit user if successful

  const user = context.user;
  if (!user || !user.id) throw new Error("User not authenticated");

  const payments = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  const users = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const payment = await payments.findOne({ _id: paymentId, user_id: user.id });

  if (!payment) {
    throw new Error("Payment not found");
  }

  if (payment.status === 'succeeded' || payment.status === 'confirmed') {
    return { status: 'succeeded' };
  }

  if (payment.status === 'canceled') {
    return { status: 'canceled' };
  }

  // Call Yookassa to check status
  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");
  const authString = Buffer.from(`${shopId}:${secretKey}`).toString('base64');

  const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${payment.yookassa_id}`,
    headers: {
      "Authorization": [`Basic ${authString}`]
    }
  });

  if (response.statusCode >= 300) {
    throw new Error(`Yookassa error: ${response.body.text()}`);
  }

  const responseBody = JSON.parse(response.body.text());
  const newStatus = responseBody.status;

  if (newStatus === 'succeeded') {
    // Atomically update payment status and user balance
    // But we need to update two collections.
    // Use the "Update Payment First" strategy.

    const updatedPayment = await payments.findOneAndUpdate(
      { _id: paymentId, status: { $ne: 'succeeded' } },
      { $set: { status: 'succeeded', paid_at: new Date() } },
      { returnNewDocument: true }
    );

    if (updatedPayment) {
      // If we successfully updated payment from pending -> succeeded, credit balance
      await users.updateOne(
        { _id: user.id },
        { $inc: { balance: payment.amount } }
      );
    }
  } else if (newStatus === 'canceled') {
    await payments.updateOne(
      { _id: paymentId },
      { $set: { status: 'canceled' } }
    );
  }

  return { status: newStatus };
};
