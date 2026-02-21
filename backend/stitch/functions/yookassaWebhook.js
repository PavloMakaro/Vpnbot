exports = async function(request, response) {
  const body = JSON.parse(request.body.text());
  const event = body.event;
  const payment = body.object;

  if (event === "payment.succeeded") {
    const paymentId = payment.id;
    const amount = parseFloat(payment.amount.value);
    const userId = payment.metadata.user_id;

    const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
    const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

    // Check if payment already processed
    const existingPayment = await paymentsCollection.findOne({ _id: paymentId });
    if (existingPayment && existingPayment.status === "succeeded") {
      response.setStatusCode(200);
      response.setBody("Already processed");
      return;
    }

    // Update payment status
    await paymentsCollection.updateOne(
      { _id: paymentId },
      { $set: { status: "succeeded", updated_at: new Date() } }
    );

    // Update user balance
    await usersCollection.updateOne(
      { telegram_id: userId },
      { $inc: { balance: amount } }
    );

    // Optionally notify user via bot if possible (e.g. store notification task or call bot API)
    // context.functions.execute("notifyUser", userId, "Balance topped up by " + amount);

    response.setStatusCode(200);
    response.setBody("OK");
  } else {
    response.setStatusCode(200); // Acknowledge other events
    response.setBody("Ignored");
  }
};
