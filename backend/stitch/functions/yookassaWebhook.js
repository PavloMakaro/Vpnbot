exports = async function(payload, response) {
  // Hook this to an HTTP Service Incoming Webhook
  const body = EJSON.parse(payload.body.text());

  if (body.event === 'payment.succeeded') {
    const payment = body.object;
    const userId = payment.metadata.user_id;
    const amount = parseFloat(payment.amount.value);

    const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
    const existing = await paymentsCollection.findOne({ _id: payment.id });

    if (existing && existing.status === 'succeeded') {
        response.setStatusCode(200);
        return;
    }

    // Update Payment
    await paymentsCollection.updateOne(
      { _id: payment.id },
      { $set: { status: 'succeeded', updated_at: new Date() } },
      { upsert: true } // Just in case
    );

    // Update User Balance
    if (userId) {
       const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
       await usersCollection.updateOne(
         { _id: userId },
         { $inc: { balance: amount } }
       );
    }
  }

  response.setStatusCode(200);
};
