exports = async function(request, response) {
  try {
    const body = JSON.parse(request.body.text());
    const event = body.object;

    if (body.event !== 'payment.succeeded') {
      response.setStatusCode(200);
      return;
    }

    const paymentId = event.id;
    const amount = parseFloat(event.amount.value);
    const userId = event.metadata.user_id;

    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    const payments = db.collection("payments");
    const users = db.collection("users");

    // Check if payment already processed
    const payment = await payments.findOne({ _id: paymentId });

    if (!payment) {
      // Payment not found in our DB? Maybe create it or log error
      console.error(`Payment ${paymentId} not found`);
      response.setStatusCode(200); // Ack to stop retries
      return;
    }

    if (payment.status === 'succeeded') {
      response.setStatusCode(200);
      return;
    }

    // Update Payment Status
    await payments.updateOne(
      { _id: paymentId },
      {
        $set: {
          status: 'succeeded',
          updated_at: new Date(),
          yookassa_data: event
        }
      }
    );

    // Credit User Balance
    await users.updateOne(
      { _id: userId },
      { $inc: { balance: amount } }
    );

    // Log success
    console.log(`Payment ${paymentId} processed for user ${userId}`);

    response.setStatusCode(200);
  } catch (err) {
    console.error("Webhook Error:", err);
    response.setStatusCode(500);
    response.setBody(err.message);
  }
};
