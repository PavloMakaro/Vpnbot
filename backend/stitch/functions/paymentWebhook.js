exports = async function(request, response) {
  const body = JSON.parse(request.body.text());
  const type = body.type;

  if (type === "notification") {
    const object = body.object;
    if (object.status === "succeeded") {
      const paymentId = object.id;
      const db = context.services.get("mongodb-atlas").db("vpn_bot");
      const payments = db.collection("payments");
      const users = db.collection("users");

      const payment = await payments.findOne({ payment_id: paymentId });

      if (payment && payment.status !== "succeeded") {
        await payments.updateOne(
          { _id: payment._id },
          { $set: { status: "succeeded", confirmed_at: new Date() } }
        );

        await users.updateOne(
          { _id: payment.user_id },
          { $inc: { balance: payment.amount } }
        );
      }
    }
  }

  response.setStatusCode(200);
  response.setBody("OK");
};
