exports = async function(paymentId) {
    const userId = context.user.id;
    const yookassaShopId = context.values.get("YOOKASSA_SHOP_ID");
    const yookassaSecret = context.values.get("YOOKASSA_SECRET_KEY");

    const authString = Buffer.from(`${yookassaShopId}:${yookassaSecret}`).toString('base64');

    const mongodb = context.services.get("mongodb-atlas");
    const db = mongodb.db("vpn");
    const paymentsCollection = db.collection("payments");
    const usersCollection = db.collection("users");

    const paymentRecord = await paymentsCollection.findOne({ _id: paymentId, user_id: userId });

    if (!paymentRecord) {
      throw new Error("Payment record not found.");
    }

    if (paymentRecord.status === 'confirmed') {
        return { status: 'succeeded' };
    }

    const response = await context.http.get({
      url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
      headers: {
        "Authorization": [`Basic ${authString}`],
        "Content-Type": ["application/json"]
      }
    });

    if (response.statusCode >= 400) {
      console.log(`Yookassa API Error: ${response.body.text()}`);
      throw new Error("Payment check failed.");
    }

    const responseBody = JSON.parse(response.body.text());

    if (responseBody.status === 'succeeded' && paymentRecord.status !== 'confirmed') {
      // Top up user balance
      const amount = paymentRecord.amount;

      await usersCollection.updateOne(
        { _id: userId },
        { $inc: { balance: amount } }
      );

      await paymentsCollection.updateOne(
        { _id: paymentId },
        { $set: { status: 'confirmed' } }
      );

      return { status: 'succeeded' };
    } else if (responseBody.status === 'canceled') {
        await paymentsCollection.updateOne(
            { _id: paymentId },
            { $set: { status: 'canceled' } }
          );
        return { status: 'canceled' };
    }

    return { status: 'pending' };
  };