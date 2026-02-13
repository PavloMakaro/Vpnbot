exports = async function(amount, description){
  const user = context.user;
  if (!user) {
    throw new Error("User not authenticated");
  }

  const userId = user.id;

  // In production, create Values in Atlas App Services named "yookassaShopId" and "yookassaSecretKey"
  const SHOP_ID = context.values.get("yookassaShopId") || "1172989";
  const SECRET_KEY = context.values.get("yookassaSecretKey") || "live_abcZFyD5DDi8YoFafjPEJO_2TjWa5BCIWwWbSJvgrf4";

  const idempotenceKey = new Date().getTime().toString() + Math.random().toString(36).substring(7);

  const body = {
    amount: {
      value: amount.toFixed(2),
      currency: "RUB"
    },
    confirmation: {
      type: "redirect",
      return_url: "https://t.me/vpni50_bot" // Should ideally be the Mini App URL
    },
    capture: true,
    description: description,
    metadata: {
      user_id: userId,
      payment_type: "balance_topup"
    },
    receipt: {
      customer: {
        email: "no-email@example.com" // Placeholder
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

  // Use context.http
  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Content-Type": ["application/json"],
      "Idempotence-Key": [idempotenceKey],
      "Authorization": ["Basic " + Buffer.from(SHOP_ID + ":" + SECRET_KEY).toString('base64')]
    },
    body: JSON.stringify(body),
    encodeBodyAsJSON: false
  });

  if (response.statusCode !== 200 && response.statusCode !== 201) {
    throw new Error("Failed to create payment: " + response.body.text());
  }

  const paymentData = JSON.parse(response.body.text());

  // Save payment to DB
  const collection = context.services.get("mongodb-atlas").db("vpn_bot_db").collection("payments");
  await collection.insertOne({
    _id: paymentData.id,
    user_id: userId,
    amount: amount,
    status: paymentData.status, // 'pending'
    created_at: new Date(),
    confirmation_url: paymentData.confirmation.confirmation_url
  });

  return {
    payment_id: paymentData.id,
    confirmation_url: paymentData.confirmation.confirmation_url
  };
};
