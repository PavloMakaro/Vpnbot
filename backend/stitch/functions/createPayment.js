exports = async function(amount, returnUrl) {
    const userId = context.user.id;
    const yookassaShopId = context.values.get("YOOKASSA_SHOP_ID");
    const yookassaSecret = context.values.get("YOOKASSA_SECRET_KEY");

    if (!amount || amount < 50) {
      throw new Error("Invalid amount. Minimum is 50 RUB.");
    }

    const authString = Buffer.from(`${yookassaShopId}:${yookassaSecret}`).toString('base64');
    const idempotenceKey = new ObjectId().toString();

    const payload = {
      amount: {
        value: amount.toFixed(2),
        currency: "RUB"
      },
      confirmation: {
        type: "redirect",
        return_url: returnUrl || "https://t.me/vpni50_bot" // Fallback
      },
      capture: true,
      description: `Пополнение баланса на ${amount} ₽`,
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
            description: `Пополнение баланса на ${amount} ₽`,
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
        "Authorization": [`Basic ${authString}`],
        "Idempotence-Key": [idempotenceKey],
        "Content-Type": ["application/json"]
      },
      body: JSON.stringify(payload)
    });

    if (response.statusCode >= 400) {
      console.log(`Yookassa API Error: ${response.body.text()}`);
      throw new Error("Payment creation failed.");
    }

    const responseBody = JSON.parse(response.body.text());

    const mongodb = context.services.get("mongodb-atlas");
    const db = mongodb.db("vpn");
    const paymentsCollection = db.collection("payments");

    const paymentRecord = {
      _id: responseBody.id,
      user_id: userId,
      amount: amount,
      status: "pending",
      method: "yookassa_smart",
      timestamp: new Date(),
      type: "balance_topup"
    };

    await paymentsCollection.insertOne(paymentRecord);

    return {
      paymentId: responseBody.id,
      confirmationUrl: responseBody.confirmation.confirmation_url
    };
  };