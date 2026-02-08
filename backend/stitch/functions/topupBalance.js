exports = async function(arg) {
  const { amount } = arg;
  const user = context.user;
  const userId = user.id;

  if (!amount || amount < 50) {
    throw new Error("Minimum amount is 50 RUB");
  }

  // Get Shop ID and Secret Key from Values
  const shopId = context.values.get("yookassaShopId");
  const secretKey = context.values.get("yookassaSecretKey");

  // Create Payment via Yookassa API
  const idempotenceKey = new Date().getTime().toString(); // Use proper UUID in production

  const paymentData = {
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

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Authorization": ["Basic " + Buffer.from(`${shopId}:${secretKey}`).toString("base64")],
      "Idempotence-Key": [idempotenceKey],
      "Content-Type": ["application/json"]
    },
    body: paymentData,
    encodeBodyAsJSON: true
  });

  const responseBody = JSON.parse(response.body.text());

  if (response.statusCode >= 400) {
    throw new Error(`Yookassa Error: ${responseBody.description || "Unknown error"}`);
  }

  const paymentId = responseBody.id;
  const confirmationUrl = responseBody.confirmation.confirmation_url;

  // Save Pending Payment
  const payments = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  await payments.insertOne({
    _id: paymentId,
    user_id: userId,
    amount: amount,
    status: "pending",
    created_at: new Date(),
    confirmation_url: confirmationUrl
  });

  return { payment_url: confirmationUrl };
};
