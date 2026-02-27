exports = async function(amount) {
  const currentUser = context.user;
  const user_id = currentUser.id;
  const payment_id = new BSON.ObjectId().toString();

  const YOOKASSA_SHOP_ID = context.values.get("YOOKASSA_SHOP_ID");
  const YOOKASSA_SECRET_KEY = context.values.get("YOOKASSA_SECRET_KEY");
  const BOT_RETURN_URL = context.values.get("BOT_RETURN_URL"); // Get URL from values

  const body = {
    amount: {
      value: amount.toFixed(2),
      currency: "RUB"
    },
    confirmation: {
      type: "redirect",
      return_url: BOT_RETURN_URL || "https://t.me/vpni50_bot" // Fallback if not set
    },
    capture: true,
    description: `Balance topup for ${user_id}`,
    metadata: {
      user_id: user_id,
      payment_type: "balance_topup"
    },
    receipt: {
      customer: {
        email: "no-email@example.com"
      },
      items: [
        {
          description: "Balance Topup",
          quantity: "1.00",
          amount: {
            value: amount.toFixed(2),
            currency: "RUB"
          },
          vat_code: 1
        }
      ]
    }
  };

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Content-Type": ["application/json"],
      "Idempotence-Key": [payment_id],
      "Authorization": ["Basic " + Buffer.from(YOOKASSA_SHOP_ID + ":" + YOOKASSA_SECRET_KEY).toString("base64")]
    },
    body: JSON.stringify(body)
  });

  const responseData = JSON.parse(response.body.text());

  if (responseData.status === "pending") {
    const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
    await paymentsCollection.insertOne({
      _id: responseData.id,
      user_id: user_id,
      amount: amount,
      status: "pending",
      created_at: new Date(),
      confirmation_url: responseData.confirmation.confirmation_url
    });

    return {
      confirmation_url: responseData.confirmation.confirmation_url,
      payment_id: responseData.id
    };
  } else {
    throw new Error("Payment creation failed: " + JSON.stringify(responseData));
  }
};