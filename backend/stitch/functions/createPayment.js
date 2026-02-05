exports = async function(amount) {
  const user = context.user;
  if (!user) throw new Error("Not authenticated");
  const telegramId = user.custom_data.telegram_id;

  const shopId = context.values.get("yookassaShopId");
  const secretKey = context.values.get("yookassaSecretKey");

  const uuid = require('uuid');
  const idempotenceKey = uuid.v4();

  const body = {
    amount: {
      value: amount.toFixed(2),
      currency: "RUB"
    },
    capture: true,
    confirmation: {
      type: "redirect",
      return_url: "https://t.me/vpni50_bot" // Replace with your bot link
    },
    description: `Topup balance for user ${telegramId}`,
    metadata: {
      user_id: telegramId,
      type: "balance_topup"
    },
    receipt: {
        customer: {
            email: "user@example.com" // Needs a valid email or logic to get it
        },
        items: [
            {
                description: "Balance Topup",
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

  // Using Fetch API (Atlas Functions support fetch/axios if dependencies added, or built-in context.http)
  // Let's use context.http
  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Content-Type": ["application/json"],
      "Idempotence-Key": [idempotenceKey]
    },
    auth: {
        username: shopId,
        password: secretKey
    },
    body: JSON.stringify(body),
    encodeBodyAsJSON: false
  });

  const result = JSON.parse(response.body.text());

  if (result.type === "error") {
      throw new Error(result.description);
  }

  // Save payment intent to DB
  const mongodb = context.services.get("mongodb-atlas");
  await mongodb.db("vpn_bot").collection("payments").insertOne({
      _id: result.id,
      user_id: telegramId,
      amount: amount,
      status: result.status,
      created_at: new Date()
  });

  return result.confirmation.confirmation_url;
};
