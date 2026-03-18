exports = async function(amount) {
  const telegramId = context.user.identities[0].id;

  if (!telegramId) {
    throw new Error("No Telegram ID found in context");
  }

  const YOOKASSA_SHOP_ID = context.values.get("YOOKASSA_SHOP_ID");
  const YOOKASSA_SECRET_KEY = context.values.get("YOOKASSA_SECRET_KEY");

  if (!YOOKASSA_SHOP_ID || !YOOKASSA_SECRET_KEY) {
    throw new Error("Yookassa credentials are not configured");
  }

  // Idempotency key for Yookassa using standard JS Math and Date methods
  const idempotencyKey = `${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;

  const paymentPayload = {
    amount: {
      value: `${amount}.00`,
      currency: "RUB"
    },
    confirmation: {
      type: "redirect",
      return_url: "https://t.me/vpni50_bot"
    },
    capture: true,
    description: `Пополнение баланса на ${amount} ₽`,
    metadata: {
      user_id: telegramId,
      payment_type: "balance_topup"
    }
  };

  const authString = Buffer.from(`${YOOKASSA_SHOP_ID}:${YOOKASSA_SECRET_KEY}`).toString("base64");

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Authorization": [`Basic ${authString}`],
      "Idempotence-Key": [idempotencyKey],
      "Content-Type": ["application/json"]
    },
    body: paymentPayload,
    encodeBodyAsJSON: true
  });

  if (response.statusCode >= 400) {
    console.log("Yookassa Error:", response.body.text());
    throw new Error("Failed to create Yookassa payment");
  }

  const paymentData = JSON.parse(response.body.text());

  // Record payment in MongoDB
  const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  const pad = (n) => n.toString().padStart(2, '0');
  const now = new Date();
  const timestampString = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

  await paymentsCollection.insertOne({
    _id: paymentData.id,
    user_id: telegramId,
    amount: amount,
    status: "pending",
    method: "yookassa_smart",
    timestamp: timestampString,
    type: "balance_topup"
  });

  return {
    success: true,
    paymentId: paymentData.id,
    confirmationUrl: paymentData.confirmation.confirmation_url
  };
};
