exports = async function(telegramId, amount) {
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const paymentsColl = db.collection("payments");
  const usersColl = db.collection("users");

  const user = await usersColl.findOne({ _id: telegramId });
  if (!user) {
      return { success: false, message: "User not found." };
  }

  // Get credentials from Atlas context values
  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  // Basic Auth string
  const authString = Buffer.from(`${shopId}:${secretKey}`).toString("base64");

  // Generate a unique idempotence key
  const idempotenceKey = new BSON.ObjectId().toString();

  const paymentPayload = {
      amount: {
          value: `${amount}.00`,
          currency: "RUB"
      },
      confirmation: {
          type: "redirect",
          return_url: "https://t.me/vpni50_bot" // Redirect to bot
      },
      capture: true,
      description: `Пополнение баланса на ${amount} ₽`,
      metadata: {
          user_id: telegramId,
          payment_type: "balance_topup"
      },
      receipt: {
          customer: {
              email: "no-email@example.com"
          },
          items: [
              {
                  description: `Пополнение баланса на ${amount} ₽`,
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

  try {
      const response = await context.http.post({
          url: "https://api.yookassa.ru/v3/payments",
          headers: {
              "Authorization": [`Basic ${authString}`],
              "Idempotence-Key": [idempotenceKey],
              "Content-Type": ["application/json"]
          },
          body: JSON.stringify(paymentPayload)
      });

      const responseBody = EJSON.parse(response.body.text());

      if (responseBody.type && responseBody.type === "error") {
          console.error("Yookassa Error:", responseBody);
          return { success: false, message: "Error from Yookassa API." };
      }

      const paymentId = responseBody.id;
      const confirmationUrl = responseBody.confirmation.confirmation_url;

      // Save pending payment to MongoDB
      await paymentsColl.insertOne({
          _id: paymentId,
          user_id: telegramId,
          amount: amount,
          status: "pending",
          method: "yookassa_smart",
          timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
          type: "balance_topup",
          payment_id: paymentId
      });

      return {
          success: true,
          confirmation_url: confirmationUrl,
          payment_id: paymentId
      };

  } catch (error) {
      console.error("HTTP Request Error:", error);
      return { success: false, message: "Error creating payment." };
  }
};