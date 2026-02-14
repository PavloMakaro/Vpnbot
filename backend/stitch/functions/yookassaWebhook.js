exports = async function(request, response) {
  const body = JSON.parse(request.body.text());

  if (body.event === "payment.succeeded") {
    const paymentObj = body.object;
    const paymentId = paymentObj.id;

    const db = context.services.get("mongodb-atlas").db("vpn_bot_db");
    const payments = db.collection("payments");
    const users = db.collection("users");

    const payment = await payments.findOne({ _id: paymentId });

    if (payment && payment.status !== "succeeded") {
      // Update payment status
      await payments.updateOne(
        { _id: paymentId },
        { $set: { status: "succeeded", updated_at: new Date() } }
      );

      // Credit User Balance
      await users.updateOne(
        { _id: payment.user_id },
        { $inc: { balance: payment.amount } }
      );

      console.log(`Payment ${paymentId} succeeded. User ${payment.user_id} credited.`);
    }
  }

  response.setStatusCode(200);
  response.setBody("OK");
};
