exports = async function(amount) {
  const user_id = context.user.id;

  // Retrieve secrets from Atlas App Services Values
  const shopId = context.values.get("yookassaShopId");
  const secretKey = context.values.get("yookassaSecretKey");

  if (!shopId || !secretKey) {
      throw new Error("Yookassa credentials not configured in App Services Values.");
  }

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Content-Type": ["application/json"],
      "Idempotence-Key": [new Date().getTime().toString() + Math.random()],
      "Authorization": ["Basic " + Buffer.from(shopId + ":" + secretKey).toString('base64')]
    },
    body: JSON.stringify({
      amount: {
        value: Number(amount).toFixed(2),
        currency: "RUB"
      },
      capture: true,
      confirmation: {
        type: "redirect",
        return_url: "https://t.me/vpni50_bot"
      },
      description: "Balance top-up for user " + user_id,
      metadata: {
        user_id: user_id.toString()
      }
    })
  });

  const body = EJSON.parse(response.body.text());

  if (response.statusCode >= 200 && response.statusCode < 300) {
    const db = context.services.get("mongodb-atlas").db("vpn_bot");
    await db.collection("payments").insertOne({
      payment_id: body.id,
      user_id: user_id,
      amount: Number(amount),
      status: "pending",
      created_at: new Date()
    });

    return { confirmation_url: body.confirmation.confirmation_url };
  } else {
    throw new Error("Payment creation failed: " + JSON.stringify(body));
  }
};
