exports = async function(amount) {
  const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");

  // Use Authenticated User ID
  const userId = context.user.id;
  if (!userId) return { error: "Not authenticated" };

  // 1. Get Secrets
  let SHOP_ID, SECRET_KEY;
  try {
    SHOP_ID = context.values.get("YOOKASSA_SHOP_ID");
    SECRET_KEY = context.values.get("YOOKASSA_SECRET_KEY");
  } catch(e) {
    return { error: "Yookassa credentials not configured" };
  }

  // 2. Prepare Request
  const idempotenceKey = new Date().getTime().toString();
  const credentials = Buffer.from(`${SHOP_ID}:${SECRET_KEY}`).toString('base64');

  const body = {
    amount: {
      value: Number(amount).toFixed(2),
      currency: "RUB"
    },
    capture: true,
    confirmation: {
      type: "redirect",
      return_url: "https://t.me/vpni50_bot"
    },
    description: `Пополнение баланса ID: ${userId}`,
    metadata: {
      user_id: userId.toString(),
      type: "balance_topup"
    }
  };

  // 3. Call Yookassa API
  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Authorization": `Basic ${credentials}`,
      "Idempotence-Key": idempotenceKey,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body),
    encodeBodyAsJSON: false
  });

  const responseBody = EJSON.parse(response.body.text());

  if (response.status >= 400) {
    return { error: responseBody.description || "Payment creation failed" };
  }

  // 4. Save Payment
  const paymentRecord = {
    _id: responseBody.id,
    user_id: userId,
    amount: Number(amount),
    status: responseBody.status,
    created_at: new Date(),
    confirmation_url: responseBody.confirmation.confirmation_url
  };

  await paymentsCollection.insertOne(paymentRecord);

  return {
    payment_id: responseBody.id,
    confirmation_url: responseBody.confirmation.confirmation_url
  };
};
