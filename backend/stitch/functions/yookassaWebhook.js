exports = async function(request, response) {
  // 1. Get Dependencies and Secrets
  const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  let SHOP_ID, SECRET_KEY, BOT_TOKEN;
  try {
    SHOP_ID = context.values.get("YOOKASSA_SHOP_ID");
    SECRET_KEY = context.values.get("YOOKASSA_SECRET_KEY");
    BOT_TOKEN = context.values.get("BOT_TOKEN");
  } catch(e) {
    console.error("Missing secrets");
    response.setStatusCode(500);
    return;
  }

  // 2. Parse Webhook Data
  const body = JSON.parse(request.body.text());

  if (body.event !== "payment.succeeded") {
    response.setStatusCode(200); // Acknowledge other events
    return;
  }

  const paymentId = body.object.id;

  // 3. Verify Payment with Yookassa API (Double Check)
  const credentials = Buffer.from(`${SHOP_ID}:${SECRET_KEY}`).toString('base64');
  const verifyResponse = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: {
      "Authorization": `Basic ${credentials}`
    }
  });

  if (verifyResponse.status !== 200) {
    console.error("Failed to verify payment with Yookassa");
    response.setStatusCode(500);
    return;
  }

  const paymentData = EJSON.parse(verifyResponse.body.text());

  if (paymentData.status !== "succeeded") {
    console.log("Payment not succeeded yet according to API");
    response.setStatusCode(200);
    return;
  }

  // 4. Process Payment
  const existingPayment = await paymentsCollection.findOne({ _id: paymentId });

  if (!existingPayment || existingPayment.status === "succeeded") {
    console.log("Payment already processed or not found locally");
    response.setStatusCode(200);
    return;
  }

  const userId = paymentData.metadata.user_id;
  const amount = Number(paymentData.amount.value);

  // Update Payment
  await paymentsCollection.updateOne(
    { _id: paymentId },
    { $set: { status: "succeeded", updated_at: new Date() } }
  );

  // Update User Balance
  await usersCollection.updateOne(
    { _id: userId },
    { $inc: { balance: amount } }
  );

  // 5. Notify User via Telegram Bot
  try {
    await context.http.post({
      url: `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`,
      body: {
        chat_id: userId,
        text: `✅ Баланс успешно пополнен на ${amount} ₽!`
      },
      encodeBodyAsJSON: true
    });
  } catch(e) {
    console.error("Failed to send notification: " + e);
  }

  response.setStatusCode(200);
};
