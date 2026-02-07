exports = async function({ amount }) {
  const userId = context.user.id;
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");

  // YooKassa Configuration
  const YOOKASSA_SHOP_ID = "YOUR_SHOP_ID"; // Replace
  const YOOKASSA_SECRET_KEY = "YOUR_SECRET_KEY"; // Replace
  const AUTH_STRING = Buffer.from(`${YOOKASSA_SHOP_ID}:${YOOKASSA_SECRET_KEY}`).toString('base64');

  const idempotenceKey = new BSON.ObjectId().toString();

  try {
    const response = await context.http.post({
      url: "https://api.yookassa.ru/v3/payments",
      headers: {
        "Authorization": `Basic ${AUTH_STRING}`,
        "Idempotence-Key": idempotenceKey,
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
          return_url: "https://t.me/YOUR_BOT_USERNAME/app" // Replace with your Mini App link
        },
        description: `Top up balance for User ${userId}`,
        metadata: {
          user_id: userId
        }
      },
      encodeBodyAsJSON: true
    });

    const paymentData = JSON.parse(response.body.text());

    if (paymentData.status === "pending") {
      await collection.insertOne({
        payment_id: paymentData.id,
        user_id: userId,
        amount: amount,
        status: "pending",
        created_at: new Date()
      });

      return {
        confirmation_url: paymentData.confirmation.confirmation_url,
        payment_id: paymentData.id
      };
    } else {
      throw new Error("Payment creation failed: " + JSON.stringify(paymentData));
    }
  } catch (err) {
    console.error("YooKassa API Error:", err);
    throw new Error("Failed to create payment");
  }
};
