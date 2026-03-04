exports = async function(amount, description, returnUrl) {
  const userId = context.user.id;
  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
    throw new Error("Yookassa credentials are not configured");
  }

  const idempotenceKey = new Date().getTime().toString() + Math.random().toString();

  const paymentPayload = {
    amount: {
      value: amount.toFixed(2),
      currency: "RUB"
    },
    confirmation: {
      type: "redirect",
      return_url: returnUrl || "https://t.me/vpni50_bot" // Default or provided
    },
    capture: true,
    description: description,
    metadata: {
      user_id: userId,
      payment_type: "balance_topup"
    },
    receipt: {
      customer: {
        email: "no-email@example.com"
      },
      items: [
        {
          description: description.substring(0, 128),
          quantity: "1.00",
          amount: {
            value: amount.toFixed(2),
            currency: "RUB"
          },
          vat_code: 1
        }
      ]
    }
  };

  const basicAuth = Buffer.from(`${shopId}:${secretKey}`).toString('base64');

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Authorization": [`Basic ${basicAuth}`],
      "Idempotence-Key": [idempotenceKey],
      "Content-Type": ["application/json"]
    },
    body: JSON.stringify(paymentPayload)
  });

  if (response.statusCode >= 400) {
    throw new Error(`Yookassa API Error: ${response.statusCode} ${response.body.text()}`);
  }

  const paymentData = JSON.parse(response.body.text());

  // Save to payments collection
  const cluster = context.services.get("mongodb-atlas");
  const paymentsCollection = cluster.db("vpn_bot").collection("payments");

  await paymentsCollection.insertOne({
    _id: paymentData.id,
    user_id: userId,
    amount: amount,
    status: "pending",
    method: "yookassa_smart",
    timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
    type: "balance_topup",
    payment_id: paymentData.id
  });

  return {
    paymentId: paymentData.id,
    confirmationUrl: paymentData.confirmation.confirmation_url
  };
};
