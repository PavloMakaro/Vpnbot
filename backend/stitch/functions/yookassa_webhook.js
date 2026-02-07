exports = async function(payload, response) {
  const body = EJSON.parse(payload.body.text());
  const event = body.event;
  const payment = body.object;

  const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  if (event === "payment.succeeded") {
    const paymentId = payment.id;
    const amount = parseFloat(payment.amount.value);
    const userId = payment.metadata.user_id; // Retrieved from metadata

    // Check if payment already processed
    const existingPayment = await paymentsCollection.findOne({ payment_id: paymentId });
    if (existingPayment && existingPayment.status === "succeeded") {
      response.setStatusCode(200);
      return;
    }

    // Update payment status
    await paymentsCollection.updateOne(
      { payment_id: paymentId },
      { $set: { status: "succeeded", updated_at: new Date() } }
    );

    // Update user balance
    await usersCollection.updateOne(
      { user_id: userId },
      { $inc: { balance: amount } }
    );
  }

  response.setStatusCode(200);
};
