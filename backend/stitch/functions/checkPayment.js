exports = async function(paymentId) {
  const telegramId = context.user.identities[0].id;
  if (!telegramId) throw new Error("Not authenticated");

  const YOOKASSA_SHOP_ID = context.values.get("YOOKASSA_SHOP_ID");
  const YOOKASSA_SECRET_KEY = context.values.get("YOOKASSA_SECRET_KEY");

  const auth = Buffer.from(`${YOOKASSA_SHOP_ID}:${YOOKASSA_SECRET_KEY}`).toString('base64');

  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const paymentsCollection = db.collection("payments");
  const usersCollection = db.collection("users");

  // Use findOneAndUpdate to atomically lock the payment for processing
  const paymentRecord = await paymentsCollection.findOneAndUpdate(
    { _id: paymentId, user_id: telegramId, status: "pending" },
    { $set: { status: "processing" } },
    { returnNewDocument: true }
  );

  if (!paymentRecord) {
     // Could be already confirmed, canceled, or not found. Just fetch current state to return.
     const existing = await paymentsCollection.findOne({ _id: paymentId, user_id: telegramId });
     if (!existing) throw new Error("Payment record not found");

     if (existing.status === "confirmed") return { status: "succeeded" };
     if (existing.status === "canceled") return { status: "canceled" };

     // If it's stuck in processing for too long, a cleanup job should revert it to pending.
     // For this request, we'll return pending to have the client check again later.
     return { status: "pending" };
  }

  try {
    const response = await context.http.get({
    url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
    headers: { "Authorization": [`Basic ${auth}`] }
  });

  if (response.statusCode >= 400) {
    throw new Error(`Yookassa API Error: ${response.statusCode}`);
  }

  const yooPayment = EJSON.parse(response.body.text());

    if (yooPayment.status === "succeeded") {
      // Update balance
      await usersCollection.updateOne(
          { telegram_id: paymentRecord.user_id },
          { $inc: { balance: paymentRecord.amount } }
      );

      // Update payment status
      await paymentsCollection.updateOne(
          { _id: paymentId },
          { $set: { status: "confirmed" } }
      );
    } else if (yooPayment.status === "canceled") {
      await paymentsCollection.updateOne(
          { _id: paymentId },
          { $set: { status: "canceled" } }
      );
    } else {
        // Still pending, unlock
        await paymentsCollection.updateOne(
          { _id: paymentId },
          { $set: { status: "pending" } }
      );
    }

    return { status: yooPayment.status };
  } catch(e) {
      // Revert status on error
      await paymentsCollection.updateOne(
          { _id: paymentId },
          { $set: { status: "pending" } }
      );
      throw e;
  }
};
