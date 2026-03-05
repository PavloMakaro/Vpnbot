exports = async function(amount, returnUrl) {
  const user = context.user;
  if (!user || !user.custom_data) {
    throw new Error("Authentication failed.");
  }

  const userId = user.custom_data._id || user.id;

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
    throw new Error("Payment gateway not configured.");
  }

  const mongodb = context.services.get("mongodb-atlas");
  const paymentsCollection = mongodb.db("vpn_bot").collection("payments");

  const idempotenceKey = new Date().getTime().toString() + Math.random().toString();
  const description = `Пополнение баланса на ${amount} ₽`;

  const requestBody = {
    amount: {
      value: `${amount}.00`,
      currency: "RUB"
    },
    confirmation: {
      type: "redirect",
      return_url: returnUrl || "https://t.me/vpni50_bot"
    },
    capture: true,
    description: description,
    metadata: {
      user_id: userId,
      payment_type: "balance_topup"
    },
    receipt: {
      customer: {
        email: "no-email@example.com"
      },
      items: [
        {
          description: description.substring(0, 128),
          quantity: "1.00",
          amount: {
            value: `${amount}.00`,
            currency: "RUB"
          },
          vat_code: 1
        }
      ]
    }
  };

  const authString = Buffer.from(`${shopId}:${secretKey}`).toString('base64');

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Idempotence-Key": [idempotenceKey],
      "Content-Type": ["application/json"],
      "Authorization": [`Basic ${authString}`]
    },
    body: JSON.stringify(requestBody)
  });

  if (response.statusCode >= 400) {
      console.error("Yookassa Error:", response.body.text());
      throw new Error(`Payment creation failed: ${response.statusCode}`);
  }

  const paymentData = JSON.parse(response.body.text());

  // Store pending payment
  await paymentsCollection.insertOne({
    _id: paymentData.id,
    user_id: userId,
    amount: amount,
    status: "pending",
    method: "yookassa_smart",
    timestamp: new Date().toISOString(),
    type: "balance_topup"
  });

  return {
    payment_id: paymentData.id,
    confirmation_url: paymentData.confirmation.confirmation_url
  };
};