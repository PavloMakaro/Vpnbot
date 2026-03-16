exports = async function(amount, description) {
  const tgId = context.user.identities[0].id;
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");
  const paymentsCollection = db.collection("payments");

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");
  const returnUrl = "https://t.me/vpni50_bot";

  if (!shopId || !secretKey) {
    throw new Error("Missing YooKassa configuration.");
  }

  const user = await usersCollection.findOne({ _id: tgId });
  if (!user) {
    throw new Error("User not found.");
  }

  const paymentData = {
    amount: {
      value: `${amount}.00`,
      currency: "RUB"
    },
    confirmation: {
      type: "redirect",
      return_url: returnUrl
    },
    capture: true,
    description: description,
    metadata: {
      user_id: tgId,
      payment_type: "balance_topup"
    },
    receipt: {
      customer: {
        email: user.email || 'no-email@example.com'
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

  const response = await context.http.post({
    url: "https://api.yookassa.ru/v3/payments",
    headers: {
      "Authorization": [`Basic ${Buffer.from(`${shopId}:${secretKey}`).toString('base64')}`],
      "Idempotence-Key": [new Date().getTime().toString()],
      "Content-Type": ["application/json"]
    },
    body: JSON.stringify(paymentData)
  });

  const body = EJSON.parse(response.body.text());

  if (response.statusCode >= 400) {
    throw new Error(`YooKassa error: ${body.description || JSON.stringify(body)}`);
  }

  await paymentsCollection.insertOne({
    _id: body.id,
    user_id: tgId,
    amount: amount,
    status: "pending",
    method: "yookassa_smart",
    timestamp: new Date().toISOString(),
    type: "balance_topup",
    payment_id: body.id,
    confirmation_url: body.confirmation.confirmation_url
  });

  return body;
};