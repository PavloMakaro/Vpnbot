exports = async function(amount, returnUrl) {
  const user = context.user;
  if (!user) throw new Error("Unauthorized");

  const identity = user.identities.find(id => id.provider_type === 'custom-function');
  const telegramId = identity ? identity.id : user.id;

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  // Use context.http to make request to Yookassa
  const idempotenceKey = new BSON.ObjectId().toString();

  const body = {
    amount: {
      value: amount.toFixed(2),
      currency: "RUB"
    },
    capture: true,
    confirmation: {
      type: "redirect",
      return_url: returnUrl || "https://t.me/vpni50_bot"
    },
    description: `Пополнение баланса (User: ${telegramId})`,
    metadata: {
      user_id: telegramId,
      type: "balance_topup"
    }
  };

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    body: body,
    encodeBodyAsJSON: true,
    headers: {
      "Authorization": "Basic " + Buffer.from(`${shopId}:${secretKey}`).toString('base64'),
      "Idempotence-Key": idempotenceKey,
      "Content-Type": "application/json"
    }
  });

  const responseBody = EJSON.parse(response.body.text());

  if (response.statusCode >= 400) {
    throw new Error(`Yookassa Error: ${JSON.stringify(responseBody)}`);
  }

  // Save pending payment
  const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  await paymentsCollection.insertOne({
    _id: responseBody.id,
    user_id: telegramId,
    amount: amount,
    status: responseBody.status,
    created_at: new Date(),
    confirmation_url: responseBody.confirmation.confirmation_url
  });

  return {
    payment_id: responseBody.id,
    confirmation_url: responseBody.confirmation.confirmation_url
  };
};
