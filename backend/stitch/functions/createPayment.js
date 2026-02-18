exports = async function(arg) {
  const amount = arg.amount;
  if (!amount || amount < 50) throw new Error("Minimum amount is 50");

  const user = context.user;
  if (!user) throw new Error("User not authenticated");
  const userId = user.id;

  const shopId = context.values.get("yookassa_shop_id");
  const secretKey = context.values.get("yookassa_secret_key");

  if (!shopId || !secretKey) throw new Error("Payment provider not configured");

  const idempotenceKey = new Date().getTime().toString(); // Simple unique key

  const payload = {
    amount: {
      value: amount.toFixed(2),
      currency: "RUB"
    },
    capture: true,
    confirmation: {
      type: "redirect",
      return_url: "https://t.me/vpni50_bot" // Replace with your bot link
    },
    description: `Topup balance for user ${userId}`,
    metadata: {
      user_id: userId,
      type: "balance_topup"
    }
  };

  // Using context.http to call Yookassa
  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Content-Type": ["application/json"],
      "Idempotence-Key": [idempotenceKey],
      // Basic Auth
      "Authorization": ["Basic " + Buffer.from(shopId + ":" + secretKey).toString('base64')]
    },
    body: payload,
    encodeBodyAsJSON: true
  });

  const responseBody = EJSON.parse(response.body.text());

  if (response.statusCode >= 400) {
    throw new Error("Payment creation failed: " + JSON.stringify(responseBody));
  }

  // Save pending payment
  const payments = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  await payments.insertOne({
    user_id: userId,
    amount: amount,
    status: "pending",
    payment_id: responseBody.id,
    created_at: new Date()
  });

  return { confirmation_url: responseBody.confirmation.confirmation_url };
};
