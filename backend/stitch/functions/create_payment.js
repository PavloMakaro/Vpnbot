exports = async function(amount) {
  if (!amount || amount < 50) {
    throw new Error("Minimum amount is 50");
  }

  const user = context.user;
  const userId = user.id;
  const shopId = context.values.get("yookassa_shop_id");
  const secretKey = context.values.get("yookassa_secret_key");

  if (!shopId || !secretKey) {
    throw new Error("YooKassa not configured");
  }

  const paymentId = new BSON.ObjectId().toString(); // Generate unique ID for our system

  const payload = {
    amount: {
      value: amount.toFixed(2),
      currency: "RUB"
    },
    capture: true,
    confirmation: {
      type: "redirect",
      return_url: "https://t.me/vpni50_bot" // Replace with your bot link
    },
    description: `Top up balance for user ${userId}`,
    metadata: {
      user_id: userId,
      internal_payment_id: paymentId
    }
  };

  // Call YooKassa API
  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Authorization": "Basic " + Buffer.from(`${shopId}:${secretKey}`).toString("base64"),
      "Idempotence-Key": paymentId,
      "Content-Type": "application/json"
    },
    body: payload,
    encodeBodyAsJSON: true
  });

  if (response.statusCode >= 200 && response.statusCode < 300) {
    const responseBody = JSON.parse(response.body.text());

    // Save pending payment to DB
    const mongodb = context.services.get("mongodb-atlas");
    const paymentsCollection = mongodb.db("vpn_bot").collection("payments");

    await paymentsCollection.insertOne({
      _id: responseBody.id, // YooKassa ID
      user_id: userId,
      amount: amount,
      status: "pending",
      created_at: new Date(),
      confirmation_url: responseBody.confirmation.confirmation_url
    });

    return {
      success: true,
      payment_id: responseBody.id,
      confirmation_url: responseBody.confirmation.confirmation_url
    };
  } else {
    console.error("YooKassa Error:", response.body.text());
    throw new Error("Failed to create payment");
  }
};
