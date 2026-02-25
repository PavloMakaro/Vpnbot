exports = async function(amount) {
  // Create a Yookassa payment

  const user = context.user;
  if (!user || !user.id) throw new Error("User not authenticated");

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
    throw new Error("Yookassa credentials not configured");
  }

  const paymentId = new BSON.ObjectId().toString(); // Internal ID

  const payload = {
    amount: {
      value: amount.toFixed(2),
      currency: "RUB"
    },
    capture: true,
    confirmation: {
      type: "redirect",
      return_url: "https://t.me/vpni50_bot" // Replace with actual bot link
    },
    description: `Topup balance for user ${user.id}`,
    metadata: {
      user_id: user.id,
      internal_payment_id: paymentId
    }
  };

  const idempotenceKey = paymentId;
  const authString = Buffer.from(`${shopId}:${secretKey}`).toString('base64');

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Authorization": [`Basic ${authString}`],
      "Idempotence-Key": [idempotenceKey],
      "Content-Type": ["application/json"]
    },
    body: payload,
    encodeBodyAsJSON: true
  });

  if (response.statusCode >= 300) {
    throw new Error(`Yookassa error: ${response.body.text()}`);
  }

  const responseBody = JSON.parse(response.body.text());

  // Store payment in DB
  const payments = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");

  await payments.insertOne({
    _id: paymentId,
    yookassa_id: responseBody.id,
    user_id: user.id,
    amount: amount,
    status: responseBody.status, // usually "pending"
    created_at: new Date(),
    confirmation_url: responseBody.confirmation.confirmation_url
  });

  return {
    payment_id: paymentId,
    confirmation_url: responseBody.confirmation.confirmation_url
  };
};
