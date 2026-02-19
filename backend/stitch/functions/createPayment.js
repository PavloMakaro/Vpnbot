exports = async function({ amount, description }) {
  const mongodb = context.services.get("mongodb-atlas");
  const payments = mongodb.db("vpn_bot").collection("payments");
  const shopId = context.values.get("yookassaShopId");
  const secretKey = context.values.get("yookassaSecretKey");

  if (!shopId || !secretKey) {
    throw new Error("Payment configuration missing");
  }

  const idempotenceKey = new BSON.ObjectId().toString();
  const authString = Buffer.from(`${shopId}:${secretKey}`).toString('base64');

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Authorization": `Basic ${authString}`,
      "Idempotence-Key": idempotenceKey,
      "Content-Type": "application/json"
    },
    body: {
      amount: {
        value: amount.toFixed(2),
        currency: "RUB"
      },
      capture: true,
      confirmation: {
        type: "redirect",
        return_url: "https://t.me/vpni50_bot" // Ideally from context value
      },
      description: description,
      metadata: {
        user_id: context.user.id
      }
    },
    encodeBodyAsJSON: true
  });

  if (response.statusCode >= 400) {
    throw new Error(`YooKassa Error: ${response.status} - ${response.body.text()}`);
  }

  const paymentData = JSON.parse(response.body.text());

  // Save to DB
  await payments.insertOne({
    _id: paymentData.id, // Use YooKassa ID as _id or store it separately
    user_id: context.user.id,
    amount: amount,
    currency: "RUB",
    status: paymentData.status,
    created_at: new Date(),
    yookassa_id: paymentData.id
  });

  return paymentData;
};
