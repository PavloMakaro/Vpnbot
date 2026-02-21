exports = async function(amount, description = "Balance top-up") {
  const user = context.user;
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Validate amount
  if (amount < 50) {
    throw new Error("Minimum amount is 50");
  }

  // Get Yookassa credentials from environment variables / Context Values
  const YOOKASSA_SHOP_ID = context.values.get("YOOKASSA_SHOP_ID");
  const YOOKASSA_SECRET_KEY = context.values.get("YOOKASSA_SECRET_KEY");

  // Create payment via Yookassa API
  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Authorization": "Basic " + Buffer.from(YOOKASSA_SHOP_ID + ":" + YOOKASSA_SECRET_KEY).toString("base64"),
      "Idempotence-Key": context.functions.uuid(), // unique for each call
      "Content-Type": "application/json"
    },
    body: {
      amount: {
        value: amount.toFixed(2),
        currency: "RUB"
      },
      capture: true,
      confirmation: {
        type: "redirect",
        return_url: "https://t.me/your_bot_username?start=payment_success" // Adjust as needed
      },
      description: description,
      metadata: {
        user_id: user.id
      }
    },
    encodeBodyAsJSON: true
  });

  const responseBody = JSON.parse(response.body.text());

  if (responseBody.status !== "pending") {
      throw new Error("Failed to create payment: " + (responseBody.description || "unknown error"));
  }

  // Store payment in database
  await collection.insertOne({
    _id: responseBody.id,
    user_id: user.id,
    amount: amount,
    status: "pending",
    created_at: new Date(),
    confirmation_url: responseBody.confirmation.confirmation_url
  });

  return responseBody.confirmation.confirmation_url;
};
