exports = async function(amount, returnUrl) {
  const telegramId = context.user.identities[0].id;
  if (!telegramId) throw new Error("Not authenticated");

  const YOOKASSA_SHOP_ID = context.values.get("YOOKASSA_SHOP_ID");
  const YOOKASSA_SECRET_KEY = context.values.get("YOOKASSA_SECRET_KEY");

  const auth = Buffer.from(`${YOOKASSA_SHOP_ID}:${YOOKASSA_SECRET_KEY}`).toString('base64');

  // Basic idempotency key generator
  const idempotenceKey = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);

  const payload = {
    amount: { value: `${amount}.00`, currency: "RUB" },
    confirmation: { type: "redirect", return_url: returnUrl },
    capture: true,
    description: `Пополнение баланса на ${amount} ₽`,
    metadata: { user_id: telegramId, payment_type: "balance_topup" }
  };

  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");
  const user = await usersCollection.findOne({ telegram_id: telegramId });

  if (user && user.email) {
      payload.receipt = {
          customer: { email: user.email },
          items: [{
              description: `Пополнение баланса на ${amount} ₽`,
              quantity: "1.00",
              amount: { value: `${amount}.00`, currency: "RUB" },
              vat_code: 1
          }]
      };
  }

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Authorization": [`Basic ${auth}`],
      "Idempotence-Key": [idempotenceKey],
      "Content-Type": ["application/json"]
    },
    body: payload,
    encodeBodyAsJSON: true
  });

  if (response.statusCode >= 400) {
    throw new Error(`Yookassa API Error: ${response.statusCode} - ${response.body.text()}`);
  }

  const paymentData = EJSON.parse(response.body.text());

  // Save payment in database
  const paymentsCollection = db.collection("payments");
  await paymentsCollection.insertOne({
    _id: paymentData.id,
    user_id: telegramId,
    amount: amount,
    status: "pending",
    method: "yookassa_smart",
    timestamp: new Date().toISOString().replace(/T/, ' ').replace(/\..+/, ''),
    type: "balance_topup",
    payment_id: paymentData.id
  });

  return { payment_id: paymentData.id, confirmation_url: paymentData.confirmation.confirmation_url };
};
