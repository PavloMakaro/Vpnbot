exports = async function(amount) {
  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
    throw new Error("YooKassa credentials not configured");
  }

  const user = context.user;
  const telegramIdentity = user.identities.find(id => id.provider_type === 'custom-function');
  if (!telegramIdentity) throw new Error("User identity not found");
  const telegramId = telegramIdentity.id;

  const paymentData = {
    amount: {
      value: Number(amount).toFixed(2),
      currency: "RUB"
    },
    capture: true,
    confirmation: {
      type: "redirect",
      return_url: "https://t.me/vpni50_bot" // You might want to update this to your bot username
    },
    description: `Balance top-up for user ${telegramId}`,
    metadata: {
      user_id: telegramId
    }
  };

  // Generate a unique key for idempotency
  const idempotenceKey = new BSON.ObjectId().toString();

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Content-Type": ["application/json"],
      "Idempotence-Key": [idempotenceKey],
      "Authorization": ["Basic " + Buffer.from(`${shopId}:${secretKey}`).toString('base64')]
    },
    body: JSON.stringify(paymentData),
    encodeBodyAsJSON: false
  });

  if (response.statusCode >= 300) {
     throw new Error(`YooKassa error: ${response.body.text()}`);
  }

  const payment = JSON.parse(response.body.text());

  const mongodb = context.services.get("mongodb-atlas");
  const paymentsCollection = mongodb.db("vpn_bot").collection("payments");

  await paymentsCollection.insertOne({
    _id: payment.id,
    user_id: telegramId,
    amount: Number(amount),
    status: 'pending',
    created_at: new Date(),
    yookassa_data: payment
  });

  return payment.confirmation.confirmation_url;
};
