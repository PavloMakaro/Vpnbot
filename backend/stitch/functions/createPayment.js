exports = async function(amount, description) {
  // Creates a payment link using Yookassa API.
  // amount: number (RUB)
  // description: string

  const shopId = context.values.get("yookassaShopId");
  const secretKey = context.values.get("yookassaSecretKey");
  const user = context.user;

  if (!shopId || !secretKey) {
    throw new Error("Yookassa credentials not configured in Atlas Values");
  }

  // Idempotency Key
  const idempotenceKey = new Date().getTime().toString();

  const payload = {
    amount: {
      value: Number(amount).toFixed(2),
      currency: "RUB"
    },
    capture: true,
    confirmation: {
      type: "redirect",
      return_url: "https://t.me/vpni50_bot" // Update with your bot username
    },
    description: description || "Balance Top-up",
    metadata: {
      user_id: user.id
    }
  };

  try {
    const response = await context.http.post({
      url: "https://api.yookassa.ru/v3/payments",
      headers: {
        "Content-Type": ["application/json"],
        "Idempotence-Key": [idempotenceKey],
        "Authorization": ["Basic " + Buffer.from(shopId + ":" + secretKey).toString('base64')]
      },
      body: JSON.stringify(payload)
    });

    const responseBody = JSON.parse(response.body.text());

    if (response.statusCode >= 200 && response.statusCode < 300) {
      // Save pending payment to DB
      const db = context.services.get("mongodb-atlas").db("vpn_bot_db");
      await db.collection("payments").insertOne({
        _id: responseBody.id,
        user_id: user.id,
        amount: Number(amount),
        status: responseBody.status, // "pending"
        created_at: new Date(),
        confirmation_url: responseBody.confirmation.confirmation_url
      });

      return {
        success: true,
        confirmation_url: responseBody.confirmation.confirmation_url,
        payment_id: responseBody.id
      };
    } else {
      console.error("Yookassa API Error:", responseBody);
      throw new Error(responseBody.description || "Payment creation failed");
    }
  } catch (err) {
    console.error("Create Payment Error:", err);
    throw err;
  }
};
