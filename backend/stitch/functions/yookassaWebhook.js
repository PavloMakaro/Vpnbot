exports = async function(payload, response) {
  // This function is intended to be called via an HTTP Endpoint (Webhook)
  // Payload is the body of the POST request from Yookassa

  const body = JSON.parse(payload.body.text());

  if (body.event === 'payment.succeeded') {
    const payment = body.object;
    const paymentId = payment.id;
    const userId = payment.metadata.user_id;
    const amount = parseFloat(payment.amount.value);

    const mongo = context.services.get("mongodb-atlas");
    const paymentsCollection = mongo.db("vpn_bot").collection("payments");
    const usersCollection = mongo.db("vpn_bot").collection("users");

    // Check if already processed
    const existingPayment = await paymentsCollection.findOne({ _id: paymentId });
    if (existingPayment && existingPayment.status === 'succeeded') {
      return; // Already processed
    }

    // Update payment status
    await paymentsCollection.updateOne(
      { _id: paymentId },
      { $set: { status: 'succeeded', finished_at: new Date() } },
      { upsert: true } // In case createPayment didn't save it yet (race condition)
    );

    // Update user balance
    await usersCollection.updateOne(
      { _id: userId },
      { $inc: { balance: amount } }
    );
  }
};
