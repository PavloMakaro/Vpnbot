exports = async function(amount) {
  const userId = context.user.id;
  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
    throw new Error("Yookassa configuration missing");
  }

  const paymentData = {
    amount: {
      value: amount.toFixed(2),
      currency: "RUB"
    },
    capture: true,
    confirmation: {
      type: "redirect",
      return_url: "https://t.me/" + context.values.get("BOT_USERNAME")
    },
    description: `Balance top-up for user ${userId}`,
    metadata: {
      user_id: userId
    }
  };

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Authorization": "Basic " + Buffer.from(`${shopId}:${secretKey}`).toString("base64"),
      "Content-Type": "application/json",
      "Idempotence-Key": new Date().getTime().toString()
    },
    body: JSON.stringify(paymentData)
  });

  const responseBody = JSON.parse(response.body.text());

  if (responseBody.status === "pending") {
    const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
    await paymentsCollection.insertOne({
      _id: responseBody.id,
      user_id: userId,
      amount: amount,
      status: "pending",
      created_at: new Date(),
      confirmation_url: responseBody.confirmation.confirmation_url
    });

    return {
      payment_url: responseBody.confirmation.confirmation_url,
      payment_id: responseBody.id
    };
  } else {
    throw new Error("Failed to create payment: " + JSON.stringify(responseBody));
  }
};
