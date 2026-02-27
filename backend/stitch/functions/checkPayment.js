exports = async function(paymentId) {
  const YOOKASSA_SHOP_ID = context.values.get("YOOKASSA_SHOP_ID");
  const YOOKASSA_SECRET_KEY = context.values.get("YOOKASSA_SECRET_KEY");

  const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: {
      "Authorization": ["Basic " + Buffer.from(YOOKASSA_SHOP_ID + ":" + YOOKASSA_SECRET_KEY).toString("base64")]
    }
  });

  const paymentData = JSON.parse(response.body.text());
  const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Check if payment is already processed to avoid Yookassa call (optional, but good for performance)
  // but we must check atomically before updating

  if (paymentData.status === "succeeded") {
    // Atomically find and update the payment ONLY IF it is still 'pending'
    const updatedPayment = await paymentsCollection.findOneAndUpdate(
      { _id: paymentId, status: "pending" },
      { $set: { status: "succeeded", completed_at: new Date() } },
      { returnNewDocument: true }
    );

    // If updatedPayment is null, it means the payment was not in 'pending' state
    // (either already processed or canceled)
    if (!updatedPayment) {
        return { status: "succeeded", message: "Payment already processed or not pending" };
    }

    // Credit user balance ONLY if the payment status update was successful
    await usersCollection.updateOne(
      { _id: updatedPayment.user_id },
      { $inc: { balance: parseFloat(updatedPayment.amount) } }
    );

    return { status: "succeeded", new_balance: parseFloat(updatedPayment.amount) };

  } else if (paymentData.status === "canceled") {
      await paymentsCollection.updateOne(
        { _id: paymentId },
        { $set: { status: "canceled", completed_at: new Date() } }
      );
      return { status: "canceled" };
  }

  return { status: paymentData.status };
};