exports = async function(amount, returnUrl) {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("User not authenticated");
  }

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
    throw new Error("Yookassa credentials are not configured");
  }

  const authHeader = "Basic " + Buffer.from(`${shopId}:${secretKey}`).toString('base64');

  // UUID for idempotence key
  function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  const paymentId = uuidv4();

  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");
  const paymentsCollection = db.collection("payments");

  const userProfile = await usersCollection.findOne({ _id: user.id });

  const email = (userProfile && userProfile.email) ? userProfile.email : 'no-email@example.com';

  const payload = {
    amount: {
      value: `${amount}.00`,
      currency: "RUB"
    },
    confirmation: {
      type: "redirect",
      return_url: returnUrl || "https://t.me/vpni50_bot" // Fallback
    },
    capture: true,
    description: `Пополнение баланса на ${amount} ₽`,
    metadata: {
      user_id: user.id,
      payment_type: "balance_topup"
    },
    receipt: {
      customer: {
        email: email
      },
      items: [
        {
          description: `Пополнение баланса на ${amount} ₽`,
          quantity: "1.00",
          amount: {
            value: `${amount}.00`,
            currency: "RUB"
          },
          vat_code: 1 // self-employed
        }
      ]
    }
  };

  try {
    const response = await context.http.post({
      url: "https://api.yookassa.ru/v3/payments",
      headers: {
        "Authorization": [authHeader],
        "Idempotence-Key": [paymentId],
        "Content-Type": ["application/json"]
      },
      body: JSON.stringify(payload)
    });

    if (response.statusCode >= 200 && response.statusCode < 300) {
      const paymentData = EJSON.parse(response.body.text());

      // Save payment intent
      await paymentsCollection.insertOne({
        _id: paymentData.id,
        user_id: user.id,
        amount: amount,
        status: "pending",
        method: "yookassa_smart",
        timestamp: new Date(),
        type: "balance_topup",
        payment_id: paymentData.id
      });

      return {
        id: paymentData.id,
        status: paymentData.status,
        confirmation_url: paymentData.confirmation ? paymentData.confirmation.confirmation_url : null
      };
    } else {
      throw new Error(`Yookassa API error: ${response.statusCode} - ${response.body.text()}`);
    }
  } catch (error) {
    throw new Error(`Failed to create payment: ${error.message}`);
  }
};