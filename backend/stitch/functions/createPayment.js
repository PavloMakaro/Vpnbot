exports = async function(amount, description, returnUrl) {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("Authentication required.");
  }

  const telegramId = user.id;

  const yookassaShopId = context.values.get("YOOKASSA_SHOP_ID");
  const yookassaSecretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!yookassaShopId || !yookassaSecretKey) {
     console.error("Yookassa credentials are not set in context values.");
     throw new Error("Internal Server Error: Missing Payment Credentials");
  }

  // Create unique payment UUID
  const crypto = require("crypto");
  const idempotencyKey = crypto.randomUUID();

  const authString = Buffer.from(`${yookassaShopId}:${yookassaSecretKey}`).toString('base64');

  const payload = {
    amount: {
      value: `${amount}.00`,
      currency: "RUB"
    },
    confirmation: {
      type: "redirect",
      return_url: returnUrl || "https://t.me/vpni50_bot"
    },
    capture: true,
    description: description,
    metadata: {
      user_id: telegramId,
      payment_type: "balance_topup"
    },
    receipt: {
      customer: {
        email: "no-email@example.com" // Provide fallback or get from user profile
      },
      items: [
        {
          description: description.substring(0, 128),
          quantity: "1.00",
          amount: {
            value: `${amount}.00`,
            currency: "RUB"
          },
          vat_code: 1
        }
      ]
    }
  };

  try {
    const response = await context.http.post({
      url: "https://api.yookassa.ru/v3/payments",
      headers: {
        "Authorization": [`Basic ${authString}`],
        "Idempotence-Key": [idempotencyKey],
        "Content-Type": ["application/json"]
      },
      body: JSON.stringify(payload)
    });

    if (response.statusCode >= 200 && response.statusCode < 300) {
      const responseBody = EJSON.parse(response.body.text());

      // Store pending payment in DB
      const mongodb = context.services.get("mongodb-atlas");
      const db = mongodb.db("vpn_bot");
      const paymentsCollection = db.collection("payments");

      await paymentsCollection.insertOne({
        _id: responseBody.id,
        user_id: telegramId,
        amount: amount,
        status: "pending",
        method: "yookassa_smart",
        timestamp: new Date().toISOString(),
        type: "balance_topup",
        payment_id: responseBody.id
      });

      return {
        success: true,
        payment_id: responseBody.id,
        confirmation_url: responseBody.confirmation.confirmation_url
      };
    } else {
      console.error(`Yookassa API Error: Status ${response.statusCode}`, response.body.text());
      throw new Error(`Payment API Error: ${response.statusCode}`);
    }
  } catch (err) {
    console.error("Error calling Yookassa API", err);
    throw err;
  }
};
