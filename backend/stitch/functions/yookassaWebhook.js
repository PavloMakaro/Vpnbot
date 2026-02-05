exports = async function(payload, response) {
  const body = EJSON.parse(payload.body.text());
  const event = body.event;
  const payment = body.object;

  if (event === "payment.succeeded") {
    const userId = payment.metadata.user_id;
    const amount = parseFloat(payment.amount.value);
    const paymentId = payment.id;

    const mongodb = context.services.get("mongodb-atlas");
    const db = mongodb.db("vpn_bot");
    const users = db.collection("users");
    const payments = db.collection("payments");

    const existingPayment = await payments.findOne({ _id: paymentId });
    if (existingPayment && existingPayment.status === "succeeded") {
        return; // Already processed
    }

    await users.updateOne(
        { _id: userId },
        { $inc: { balance: amount } }
    );

    await payments.updateOne(
        { _id: paymentId },
        { $set: { status: "succeeded", updated_at: new Date() } },
        { upsert: true }
    );
  }

  response.setStatusCode(200);
};
