exports = async function() {
  const YOOKASSA_SHOP_ID = context.values.get("YOOKASSA_SHOP_ID");
  const YOOKASSA_SECRET_KEY = context.values.get("YOOKASSA_SECRET_KEY");
  const auth = Buffer.from(`${YOOKASSA_SHOP_ID}:${YOOKASSA_SECRET_KEY}`).toString('base64');

  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const paymentsCollection = db.collection("payments");
  const usersCollection = db.collection("users");

  // Only grab payments that are pending (not processing). This acts as a basic lock if checkPayment is running.
  // Limit to 50 at a time to avoid timeout
  const pendingPayments = await paymentsCollection.find({ status: "pending", method: "yookassa_smart" }).limit(50).toArray();

  let checkedCount = 0;

  for (const payment of pendingPayments) {
    const paymentId = payment._id;

    // Atomically lock this payment to "processing" to prevent checkPayment from picking it up
    const lockedPayment = await paymentsCollection.findOneAndUpdate(
        { _id: paymentId, status: "pending" },
        { $set: { status: "processing" } }
    );

    // If it was already locked or processed by checkPayment, skip it
    if (!lockedPayment) continue;

    try {
      checkedCount++;
      const response = await context.http.get({
        url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
        headers: { "Authorization": [`Basic ${auth}`] }
      });

      if (response.statusCode >= 400) continue;

      const yooPayment = EJSON.parse(response.body.text());

      if (yooPayment.status === "succeeded") {
        // Increment user balance
        await usersCollection.updateOne(
          { telegram_id: payment.user_id },
          { $inc: { balance: payment.amount } }
        );

        // Mark payment confirmed
        await paymentsCollection.updateOne(
          { _id: paymentId },
          { $set: { status: "confirmed" } }
        );

      } else if (yooPayment.status === "canceled") {
        await paymentsCollection.updateOne(
          { _id: paymentId },
          { $set: { status: "canceled" } }
        );
      } else {
        // Still pending, unlock
        await paymentsCollection.updateOne(
          { _id: paymentId },
          { $set: { status: "pending" } }
        );
      }
    } catch (e) {
      console.error(`Error checking payment ${paymentId}: ${e.message}`);
      // Revert lock
      await paymentsCollection.updateOne(
          { _id: paymentId },
          { $set: { status: "pending" } }
      );
    }
  }

  return { checked: checkedCount };
};
