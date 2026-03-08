exports = async function(amount, description, returnUrl) {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("User not authenticated");
  }

  const telegramId = user.id;

  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");
  const paymentsCollection = mongodb.db("vpn_bot").collection("payments");

  const profile = await usersCollection.findOne({ _id: telegramId });
  if (!profile) {
    throw new Error("Profile not found");
  }

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!shopId || !secretKey) {
    throw new Error("Yookassa configuration missing in Context Values");
  }

  // Create payment request to Yookassa
  const idempKey = new BSON.ObjectId().toString();

  const body = {
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
      user_id: telegramId,
      payment_type: "balance_topup"
    },
    receipt: {
      customer: {
        email: profile.email || "no-email@example.com"
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

  const basicAuth = Buffer.from(`${shopId}:${secretKey}`).toString("base64");

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Authorization": [`Basic ${basicAuth}`],
      "Idempotence-Key": [idempKey],
      "Content-Type": ["application/json"]
    },
    body: JSON.stringify(body)
  });

  if (response.statusCode >= 400) {
    console.log(`Yookassa error: ${response.body.text()}`);
    throw new Error("Failed to create Yookassa payment");
  }

  const responseBody = JSON.parse(response.body.text());

  // Format the date to match legacy YYYY-MM-DD HH:MM:SS format
  const pad = (n) => n < 10 ? '0' + n : n;
  const now = new Date();
  const timestampFormatted = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

  // Store payment in db
  const paymentDoc = {
    _id: responseBody.id,
    user_id: telegramId,
    amount: amount,
    status: "pending",
    method: "yookassa_smart",
    timestamp: timestampFormatted,
    type: "balance_topup",
    payment_id: responseBody.id,
    confirmation_url: responseBody.confirmation.confirmation_url
  };

  await paymentsCollection.insertOne(paymentDoc);

  return paymentDoc;
};