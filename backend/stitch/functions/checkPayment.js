exports = async function(paymentId) {
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");
  const paymentsCollection = db.collection("payments");

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
    throw new Error("Missing YooKassa configuration.");
  }

  const payment = await paymentsCollection.findOne({ _id: paymentId, status: "pending" });
  if (!payment) {
    return { success: false, message: "Payment not found or already processed." };
  }

  const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: {
      "Authorization": [`Basic ${Buffer.from(`${shopId}:${secretKey}`).toString('base64')}`]
    }
  });

  const body = EJSON.parse(response.body.text());

  if (response.statusCode >= 400) {
    throw new Error(`YooKassa error: ${body.description || JSON.stringify(body)}`);
  }

  if (body.status === "succeeded") {
    // Update balance
    const updatedUser = await usersCollection.findOneAndUpdate(
      { _id: payment.user_id },
      { $inc: { balance: payment.amount } },
      { returnNewDocument: true }
    );

    await paymentsCollection.updateOne(
      { _id: paymentId },
      { $set: { status: "confirmed" } }
    );

    return { success: true, newBalance: updatedUser.balance };
  } else if (body.status === "canceled") {
    await paymentsCollection.updateOne(
      { _id: paymentId },
      { $set: { status: "canceled" } }
    );
    return { success: false, message: "Payment was canceled." };
  }

  return { success: false, message: "Payment is still pending.", status: body.status };
};