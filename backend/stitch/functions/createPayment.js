exports = async function(amount) {
  const userId = context.user.id;
  // Retrieve credentials from Atlas Context Values
  const SHOP_ID = context.values.get("yookassaShopId");
  const SECRET_KEY = context.values.get("yookassaSecretKey");

  if (!SHOP_ID || !SECRET_KEY) {
      console.error("Yookassa credentials (yookassaShopId, yookassaSecretKey) are missing in Atlas App Services configuration.");
      throw new Error("Payment configuration error.");
  }

  // Create unique payment ID
  const paymentId = new BSON.ObjectId().toString();

  const payload = {
    amount: {
      value: parseFloat(amount).toFixed(2),
      currency: "RUB"
    },
    capture: true,
    confirmation: {
      type: "redirect",
      return_url: "https://t.me/vpni50_bot" // Should be your bot or TMA link
    },
    description: `Topup balance for user ${userId}`,
    metadata: {
      user_id: userId,
      payment_type: "balance_topup"
    }
  };

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Content-Type": ["application/json"],
      "Idempotence-Key": [paymentId],
      "Authorization": ["Basic " + Buffer.from(`${SHOP_ID}:${SECRET_KEY}`).toString('base64')]
    },
    body: payload,
    encodeBodyAsJSON: true
  });

  if (response.statusCode >= 200 && response.statusCode < 300) {
    const responseBody = JSON.parse(response.body.text());

    // Save pending payment to DB
    const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
    await paymentsCollection.insertOne({
      _id: responseBody.id,
      user_id: userId,
      amount: parseFloat(amount),
      status: 'pending',
      created_at: new Date(),
      yookassa_data: responseBody
    });

    return {
      confirmation_url: responseBody.confirmation.confirmation_url
    };
  } else {
    throw new Error(`Yookassa Error: ${response.statusCode} - ${response.body.text()}`);
  }
};
