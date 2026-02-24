exports = async function(amount) {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("Unauthorized");
  }

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");
  if (!shopId || !secretKey) {
    throw new Error("Payment service not configured");
  }

  const idempotenceKey = new Date().getTime().toString() + user.id; // Unique per request

  const paymentData = {
    amount: {
      value: amount.toFixed(2),
      currency: "RUB"
    },
    confirmation: {
      type: "redirect",
      return_url: "https://t.me/vpni50_bot" // Should ideally be the Mini App link
    },
    capture: true,
    description: `Balance topup for user ${user.id}`,
    metadata: {
      user_id: user.id,
      payment_type: "balance_topup"
    }
  };

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Authorization": [`Basic ${Buffer.from(shopId + ":" + secretKey).toString("base64")}`],
      "Idempotence-Key": [idempotenceKey],
      "Content-Type": ["application/json"]
    },
    body: JSON.stringify(paymentData),
    encodeBodyAsJSON: false
  });

  const responseBody = JSON.parse(response.body.text());

  if (response.statusCode >= 200 && response.statusCode < 300) {
    // Save payment intent to DB for tracking
    const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
    await paymentsCollection.insertOne({
      _id: responseBody.id,
      user_id: user.id,
      amount: amount,
      status: responseBody.status,
      created_at: new Date(),
      confirmation_url: responseBody.confirmation.confirmation_url
    });

    return { confirmation_url: responseBody.confirmation.confirmation_url, payment_id: responseBody.id };
  } else {
    console.error("Yookassa Error:", JSON.stringify(responseBody));
    throw new Error("Payment creation failed");
  }
};
