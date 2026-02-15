exports = async function(paymentId) {
  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const payment = await paymentsCollection.findOne({ _id: paymentId });

  if (!payment) {
    throw new Error("Payment not found");
  }

  if (payment.status === "succeeded") {
    return { status: "succeeded" };
  }

  // Check with Yookassa API
  const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: {
      "Authorization": "Basic " + Buffer.from(`${shopId}:${secretKey}`).toString("base64")
    }
  });

  const responseBody = JSON.parse(response.body.text());

  if (responseBody.status === "succeeded") {
     // Atomic update to ensure we credit only once
     const updateResult = await paymentsCollection.updateOne(
       { _id: paymentId, status: { $ne: "succeeded" } },
       { $set: { status: "succeeded", updated_at: new Date() } }
     );

     if (updateResult.modifiedCount === 1) {
         // Credit User Balance
         await usersCollection.updateOne(
           { _id: payment.user_id },
           { $inc: { balance: payment.amount } }
         );
     }

     return { status: "succeeded" };
  }

  return { status: responseBody.status };
};
