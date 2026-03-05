exports = async function(paymentId) {
  const user = context.user;
  if (!user || !user.custom_data) {
    throw new Error("Authentication failed.");
  }

  const userId = user.custom_data._id || user.id;

  const mongodb = context.services.get("mongodb-atlas");
  const paymentsCollection = mongodb.db("vpn_bot").collection("payments");
  const usersCollection = mongodb.db("vpn_bot").collection("users");

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
    throw new Error("Payment gateway not configured.");
  }

  // Find payment in our DB
  const pendingPayment = await paymentsCollection.findOne({ _id: paymentId, user_id: userId });
  if (!pendingPayment) {
    throw new Error("Payment not found or you don't have permission.");
  }

  if (pendingPayment.status !== "pending") {
    return { status: pendingPayment.status, amount: pendingPayment.amount };
  }

  const authString = Buffer.from(`${shopId}:${secretKey}`).toString('base64');

  // Check with Yookassa
  const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: {
      "Authorization": [`Basic ${authString}`]
    }
  });

  if (response.statusCode >= 400) {
      console.error("Yookassa Check Error:", response.body.text());
      throw new Error(`Payment verification failed: ${response.statusCode}`);
  }

  const paymentData = JSON.parse(response.body.text());

  if (paymentData.status === "succeeded") {
    // Top up balance
    await usersCollection.updateOne(
      { _id: userId },
      { $inc: { balance: pendingPayment.amount } }
    );

    // Update payment status
    await paymentsCollection.updateOne(
      { _id: paymentId },
      { $set: { status: "confirmed" } }
    );

    return { status: "confirmed", amount: pendingPayment.amount };
  } else if (paymentData.status === "canceled") {
    // Mark as canceled
    await paymentsCollection.updateOne(
      { _id: paymentId },
      { $set: { status: "canceled" } }
    );
    return { status: "canceled", amount: pendingPayment.amount };
  }

  return { status: paymentData.status, amount: pendingPayment.amount };
};