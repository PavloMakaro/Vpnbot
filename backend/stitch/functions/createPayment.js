exports = async function(amount, returnUrl) {
  const telegramId = context.user.identities[0].id;

  if (!amount || amount < 50 || amount > 50000) {
    throw new Error("Invalid amount. Must be between 50 and 50000 RUB.");
  }

  const yookassaShopId = context.values.get("YOOKASSA_SHOP_ID");
  const yookassaSecret = context.values.get("YOOKASSA_SECRET_KEY");

  if (!yookassaShopId || !yookassaSecret) {
    throw new Error("YooKassa credentials are not configured.");
  }

  // Create Idempotency Key
  const idempotencyKey = "pay_" + Date.now().toString() + "_" + Math.floor(Math.random() * 10000).toString();

  // Format Payload
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
    description: `Balance topup for ${amount} RUB`,
    metadata: {
      user_id: telegramId,
      payment_type: "balance_topup"
    }
  };

  // HTTP call to YooKassa
  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Content-Type": ["application/json"],
      "Idempotence-Key": [idempotencyKey],
      "Authorization": ["Basic " + Buffer.from(`${yookassaShopId}:${yookassaSecret}`).toString('base64')]
    },
    body: payload,
    encodeBodyAsJSON: true
  });

  if (response.statusCode >= 400) {
     console.error("YooKassa Error: ", response.body.text());
     throw new Error("Failed to create YooKassa payment.");
  }

  const paymentData = EJSON.parse(response.body.text());

  // Store Pending Payment
  const mongodb = context.services.get("mongodb-atlas");
  const paymentsCol = mongodb.db("vpn_bot").collection("payments");

  const issueDateStr = new Date().toISOString().replace('T', ' ').substring(0, 19);

  await paymentsCol.insertOne({
    _id: paymentData.id,
    user_id: telegramId,
    amount: amount,
    status: "pending",
    method: "yookassa_smart",
    timestamp: issueDateStr,
    type: "balance_topup",
    payment_id: paymentData.id
  });

  return {
    paymentId: paymentData.id,
    confirmationUrl: paymentData.confirmation.confirmation_url
  };
};