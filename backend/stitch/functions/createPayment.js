exports = async function(amount) {
  const shopId = context.values.get("yookassaShopId");
  const secretKey = context.values.get("yookassaSecretKey");

  if (!shopId || !secretKey) {
    throw new Error("YooKassa credentials not configured.");
  }

  const idempotenceKey = new Date().getTime().toString();

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Content-Type": ["application/json"],
      "Idempotence-Key": [idempotenceKey],
      "Authorization": ["Basic " + Buffer.from(shopId + ":" + secretKey).toString('base64')]
    },
    body: JSON.stringify({
      amount: {
        value: amount.toFixed(2),
        currency: "RUB"
      },
      capture: true,
      confirmation: {
        type: "redirect",
        return_url: "https://t.me/vpni50_bot/app" // Adjust to your mini app link
      },
      description: `Balance Top-up ${amount} RUB`
    })
  });

  const responseBody = EJSON.parse(response.body.text());

  if (response.statusCode >= 400) {
    throw new Error(`YooKassa Error: ${responseBody.description || "Unknown error"}`);
  }

  // Save pending payment to DB
  const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot_db").collection("payments");
  await paymentsCollection.insertOne({
    _id: responseBody.id,
    user_id: context.user.id,
    amount: amount,
    status: "pending",
    created_at: new Date()
  });

  return {
    payment_id: responseBody.id,
    confirmation_url: responseBody.confirmation.confirmation_url
  };
};
