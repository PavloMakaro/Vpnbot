exports = async function(amount) {
  const user = context.user;
  const http = context.services.get("http");

  const shopId = context.values.get("yookassaShopId");
  const secretKey = context.values.get("yookassaSecretKey");

  if (!shopId || !secretKey) {
    throw new Error("Yookassa configuration missing");
  }

  const idempotenceKey = new BSON.ObjectId().toString();

  const response = await http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Content-Type": ["application/json"],
      "Idempotence-Key": [idempotenceKey],
      "Authorization": ["Basic " + Buffer.from(shopId + ":" + secretKey).toString("base64")]
    },
    body: {
      amount: {
        value: amount.toFixed(2),
        currency: "RUB"
      },
      capture: true,
      confirmation: {
        type: "redirect",
        return_url: "https://t.me/vpni50_bot" // Replace with your bot link
      },
      description: `Top-up balance for user ${user.id}`,
      metadata: {
        user_id: user.id
      }
    },
    encodeBodyAsJSON: true
  });

  const responseBody = JSON.parse(response.body.text());

  if (response.status !== 200) {
      throw new Error(`Yookassa Error: ${responseBody.description || responseBody.code}`);
  }

  // Save pending payment
  const payments = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  await payments.insertOne({
    user_id: user.id,
    payment_id_yookassa: responseBody.id,
    amount: parseFloat(amount),
    status: responseBody.status,
    created_at: new Date()
  });

  return {
    payment_url: responseBody.confirmation.confirmation_url,
    payment_id: responseBody.id
  };
};
