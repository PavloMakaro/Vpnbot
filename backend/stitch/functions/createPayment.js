exports = async function(amount, returnUrl) {
  const user = context.user;
  if (!user || !user.identities || user.identities.length === 0) {
    throw new Error("User not authenticated properly.");
  }

  // Extract custom identity ID which is the Telegram ID
  const telegramId = user.identities[0].id;

  const SHOP_ID = context.values.get("YOOKASSA_SHOP_ID");
  const SECRET_KEY = context.values.get("YOOKASSA_SECRET_KEY");

  if (!SHOP_ID || !SECRET_KEY) {
    throw new Error("Yookassa credentials are not configured.");
  }

  const uuidv4 = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  };

  const idempotenceKey = uuidv4();
  const auth = "Basic " + Buffer.from(SHOP_ID + ":" + SECRET_KEY).toString("base64");

  const payload = {
    amount: {
      value: `${amount}.00`,
      currency: "RUB"
    },
    confirmation: {
      type: "redirect",
      return_url: returnUrl || "https://t.me/vpni50_bot" // Default fallback
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

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Authorization": [auth],
      "Idempotence-Key": [idempotenceKey],
      "Content-Type": ["application/json"]
    },
    body: JSON.stringify(payload)
  });

  if (response.statusCode >= 200 && response.statusCode < 300) {
    const paymentData = JSON.parse(response.body.text());

    // Save pending payment to DB
    const mongodb = context.services.get("mongodb-atlas");
    const paymentsCollection = mongodb.db("vpn_bot").collection("payments");

    function pad(num) {
        return num.toString().padStart(2, '0');
    }
    const now = new Date();
    const timestamp = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

    await paymentsCollection.insertOne({
      payment_id: paymentData.id,
      user_id: telegramId,
      amount: amount,
      status: "pending",
      method: "yookassa_smart",
      timestamp: timestamp,
      type: "balance_topup"
    });

    return {
      success: true,
      payment_id: paymentData.id,
      confirmation_url: paymentData.confirmation.confirmation_url
    };
  } else {
    console.error(`Yookassa API Error: ${response.statusCode} - ${response.body.text()}`);
    return { success: false, message: "Failed to create payment" };
  }
};
