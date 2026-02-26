exports = async function(paymentId) {
  const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
      console.error("Yookassa credentials not set");
      throw new Error("Internal server error");
  }

  // Find payment in DB
  const payment = await paymentsCollection.findOne({ _id: paymentId });
  if (!payment) {
      throw new Error("Payment not found");
  }

  if (payment.status === 'succeeded') {
      return { status: 'succeeded' };
  }

  // Check Yookassa
  const response = await context.http.get({
      url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
      headers: {
          "Authorization": ["Basic " + Buffer.from(shopId + ":" + secretKey).toString('base64')]
      }
  });

  const responseBody = JSON.parse(response.body.text());

  if (response.statusCode >= 200 && response.statusCode < 300) {
      if (responseBody.status === 'succeeded' && payment.status !== 'succeeded') {
          // Update payment status
          await paymentsCollection.updateOne(
              { _id: paymentId },
              { $set: { status: 'succeeded', paid_at: new Date() } }
          );

          // Credit User
          await usersCollection.updateOne(
              { _id: payment.user_id },
              { $inc: { balance: payment.amount } }
          );

          return { status: 'succeeded' };
      } else if (responseBody.status === 'canceled') {
          await paymentsCollection.updateOne(
              { _id: paymentId },
              { $set: { status: 'canceled' } }
          );
          return { status: 'canceled' };
      }
      return { status: responseBody.status };
  } else {
      throw new Error("Failed to check payment status: " + (responseBody.description || "Unknown error"));
  }
};
