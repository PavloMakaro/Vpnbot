exports = async function(amount, description, returnUrl) {
  const shopId = context.values.get("yookassaShopId");
  const secretKey = context.values.get("yookassaSecretKey");

  if (!shopId || !secretKey) {
    // For demo/dev purposes, use mock if not configured
    // throw new Error("Yookassa credentials not configured");
    console.warn("Yookassa credentials missing. Returning mock URL.");
    return "https://yookassa.ru/checkout?mock=true";
  }

  const idempotenceKey = new Date().getTime().toString();

  // Basic Auth header
  const authString = `${shopId}:${secretKey}`;
  const authHeader = `Basic ${Buffer.from(authString).toString('base64')}`;

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Content-Type": ["application/json"],
      "Idempotence-Key": [idempotenceKey],
      "Authorization": [authHeader]
    },
    body: {
      amount: {
        value: Number(amount).toFixed(2),
        currency: "RUB"
      },
      capture: true,
      confirmation: {
        type: "redirect",
        return_url: returnUrl || "https://t.me/vpni50_bot"
      },
      description: description,
      metadata: {
        user_id: context.user.id
      }
    },
    encodeBodyAsJSON: true
  });

  if (response.statusCode >= 400) {
     const errBody = EJSON.parse(response.body.text());
     throw new Error(`Yookassa error: ${errBody.description || response.status}`);
  }

  const payment = EJSON.parse(response.body.text());

  // Save payment to DB
  const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  await paymentsCollection.insertOne({
    _id: payment.id,
    user_id: context.user.id,
    amount: parseFloat(payment.amount.value),
    status: payment.status,
    created_at: new Date()
  });

  return payment.confirmation.confirmation_url;
};
