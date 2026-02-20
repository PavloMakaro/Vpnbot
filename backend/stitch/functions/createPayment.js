exports = async function(amount) {
  const userId = context.user.id;
  const shopId = context.values.get("yookassaShopId");
  const secretKey = context.values.get("yookassaSecretKey");

  if (!shopId || !secretKey) {
    throw new Error("YooKassa credentials not configured");
  }

  // 1. Create Idempotence Key
  const idempotenceKey = new BSON.ObjectId().toString();

  // 2. Prepare Request
  const body = {
    amount: {
      value: Number(amount).toFixed(2),
      currency: "RUB"
    },
    capture: true,
    confirmation: {
      type: "redirect",
      return_url: "https://t.me/vpni50_bot" // Replace with actual bot link
    },
    description: "Balance Topup",
    metadata: {
      user_id: userId
    }
  };

  // 3. Call YooKassa API
  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Content-Type": ["application/json"],
      "Idempotence-Key": [idempotenceKey],
      "Authorization": ["Basic " + Buffer.from(`${shopId}:${secretKey}`).toString('base64')]
    },
    body: JSON.stringify(body),
    encodeBodyAsJSON: false
  });

  if (response.statusCode >= 400) {
    throw new Error(`YooKassa API Error: ${response.body.text()}`);
  }

  const paymentData = JSON.parse(response.body.text());

  // 4. Save Payment Record
  const payments = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  await payments.insertOne({
    _id: paymentData.id,
    user_id: userId,
    amount: Number(amount),
    status: "pending",
    created_at: new Date(),
    yookassa_response: paymentData
  });

  return {
    confirmation_url: paymentData.confirmation.confirmation_url
  };
};
