exports = async function(paymentId) {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("User not authenticated");
  }

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
    throw new Error("Yookassa credentials are not configured");
  }

  const authHeader = "Basic " + Buffer.from(`${shopId}:${secretKey}`).toString('base64');

  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");
  const paymentsCollection = db.collection("payments");

  // Fetch from our DB first
  const paymentRecord = await paymentsCollection.findOne({ _id: paymentId, user_id: user.id });
  if (!paymentRecord) {
    throw new Error("Payment not found");
  }

  if (paymentRecord.status === 'confirmed') {
    return { status: 'confirmed', amount: paymentRecord.amount };
  }

  if (paymentRecord.status === 'canceled' || paymentRecord.status === 'rejected') {
    return { status: paymentRecord.status };
  }

  // If pending, check Yookassa API
  try {
    const response = await context.http.get({
      url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
      headers: {
        "Authorization": [authHeader]
      }
    });

    if (response.statusCode >= 200 && response.statusCode < 300) {
      const paymentData = EJSON.parse(response.body.text());

      if (paymentData.status === 'succeeded') {
        // Atomic update of payment status
        const updateResult = await paymentsCollection.updateOne(
          { _id: paymentId, status: 'pending' },
          { $set: { status: 'confirmed' } }
        );

        if (updateResult.modifiedCount === 1) {
          // Update user balance
          await usersCollection.updateOne(
            { _id: user.id },
            { $inc: { balance: paymentRecord.amount } }
          );

          return { status: 'confirmed', amount: paymentRecord.amount };
        } else {
          // Payment might have been confirmed by a webhook or parallel process
          return { status: 'confirmed', amount: paymentRecord.amount };
        }
      } else if (paymentData.status === 'canceled') {
        await paymentsCollection.updateOne(
          { _id: paymentId },
          { $set: { status: 'canceled' } }
        );
        return { status: 'canceled' };
      } else {
        return { status: 'pending' };
      }
    } else {
      throw new Error(`Yookassa API error: ${response.statusCode} - ${response.body.text()}`);
    }
  } catch (error) {
    throw new Error(`Failed to check payment status: ${error.message}`);
  }
};