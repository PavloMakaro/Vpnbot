exports = async function(payload, response) {
  // This function is intended to be run as a Webhook (HTTP Endpoint)
  // Payload is the body of the POST request from Yookassa

  const body = EJSON.parse(payload.body.text());
  const event = body.event;
  const object = body.object;

  if (event === 'payment.succeeded' && object.status === 'succeeded') {
    const userId = object.metadata.user_id;
    const amount = parseFloat(object.amount.value);
    const paymentId = object.id;

    const payments = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
    const users = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

    // Check if already processed
    const existingPayment = await payments.findOne({ payment_id: paymentId });
    if (existingPayment && existingPayment.status === 'confirmed') {
      return; // Already processed
    }

    // Update payment status
    await payments.updateOne(
      { payment_id: paymentId },
      { $set: { status: 'confirmed', confirmed_at: new Date() } }
    );

    // Topup User Balance
    await users.updateOne(
      { _id: userId },
      { $inc: { balance: amount } }
    );
  }

  response.setStatusCode(200);
  response.setBody("OK");
};
