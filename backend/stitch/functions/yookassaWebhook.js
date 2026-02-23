exports = async function(request, response) {
  // This function should be configured as an HTTPS Endpoint in Atlas App Services
  // with method POST and path /webhook/yookassa

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  // In a real app, verify the IP or signature if possible, but YooKassa uses Basic Auth or just relies on the secret URL if no auth.
  // Atlas HTTP endpoints can be protected.

  const event = JSON.parse(request.body.text());

  if (event.type === 'notification' && event.event === 'payment.succeeded') {
    const paymentId = event.object.id;
    // The amount in event.object.amount.value is a string "100.00"

    const mongodb = context.services.get("mongodb-atlas");
    const paymentsCollection = mongodb.db("vpn_bot").collection("payments");
    const usersCollection = mongodb.db("vpn_bot").collection("users");

    const payment = await paymentsCollection.findOne({ _id: paymentId });

    if (payment) {
        if (payment.status !== 'succeeded') {
          await paymentsCollection.updateOne(
            { _id: paymentId },
            { $set: { status: 'succeeded', updated_at: new Date() } }
          );

          await usersCollection.updateOne(
            { _id: payment.user_id },
            { $inc: { balance: payment.amount } }
          );
        }
    } else {
        console.log(`Payment ${paymentId} not found in database via webhook.`);
        // Might be a payment created outside of this flow or before DB insert
    }
  }

  response.setStatusCode(200);
};
