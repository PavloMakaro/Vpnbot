exports = async function(amount, description) {
  const paymentsCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("payments");
  const userId = context.user.id;

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
      console.error("Yookassa credentials not set in context values");
      throw new Error("Internal server error");
  }

  // Generate idempotence key
  const idempotenceKey = new BSON.ObjectId().toString();

  const payload = {
      amount: {
          value: Number(amount).toFixed(2),
          currency: "RUB"
      },
      capture: true,
      confirmation: {
          type: "redirect",
          return_url: "https://t.me/vpni50_bot" // You might want to make this configurable
      },
      description: description,
      metadata: {
          user_id: userId
      },
      receipt: {
          customer: {
              email: "no-email@example.com" // Provide a default or fetch from user if possible
          },
          items: [
              {
                  description: description.substring(0, 128),
                  quantity: "1.00",
                  amount: {
                      value: Number(amount).toFixed(2),
                      currency: "RUB"
                  },
                  vat_code: 1
              }
          ]
      }
  };

  // Call Yookassa API
  const response = await context.http.post({
      url: "https://api.yookassa.ru/v3/payments",
      headers: {
          "Content-Type": ["application/json"],
          "Idempotence-Key": [idempotenceKey],
          "Authorization": ["Basic " + Buffer.from(shopId + ":" + secretKey).toString('base64')]
      },
      body: JSON.stringify(payload)
  });

  const responseBody = JSON.parse(response.body.text());

  if (response.statusCode >= 200 && response.statusCode < 300) {
      // Save payment
      await paymentsCollection.insertOne({
          _id: responseBody.id,
          user_id: userId,
          amount: Number(amount),
          status: responseBody.status, // 'pending'
          created_at: new Date(),
          confirmation_url: responseBody.confirmation.confirmation_url
      });

      return responseBody.confirmation.confirmation_url;
  } else {
      console.error("Yookassa Error:", JSON.stringify(responseBody));
      throw new Error("Payment creation failed: " + (responseBody.description || "Unknown error"));
  }
};
