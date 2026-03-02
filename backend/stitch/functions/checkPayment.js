exports = async function(paymentId) {
  const user = context.user;
  if (!user || !user.id) {
    throw new Error("Authentication required.");
  }

  const telegramId = user.id;

  const yookassaShopId = context.values.get("YOOKASSA_SHOP_ID");
  const yookassaSecretKey = context.values.get("YOOKASSA_SECRET_KEY");

  if (!yookassaShopId || !yookassaSecretKey) {
     console.error("Yookassa credentials are not set in context values.");
     throw new Error("Internal Server Error: Missing Payment Credentials");
  }

  const mongodb = context.services.get("mongodb-atlas");
  const db = mongodb.db("vpn_bot");
  const paymentsCollection = db.collection("payments");
  const usersCollection = db.collection("users");

  const paymentRecord = await paymentsCollection.findOne({ _id: paymentId, user_id: telegramId });

  if (!paymentRecord) {
    throw new Error("Payment record not found.");
  }

  if (paymentRecord.status !== "pending") {
    return {
      success: true,
      status: paymentRecord.status,
      message: `Payment is already ${paymentRecord.status}.`
    };
  }

  const authString = Buffer.from(`${yookassaShopId}:${yookassaSecretKey}`).toString('base64');

  try {
    const response = await context.http.get({
      url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
      headers: {
        "Authorization": [`Basic ${authString}`]
      }
    });

    if (response.statusCode >= 200 && response.statusCode < 300) {
      const paymentInfo = EJSON.parse(response.body.text());
      const amount = parseFloat(paymentInfo.amount.value);

      if (paymentInfo.status === "succeeded") {
        // Atomic balance update
        const updatedUser = await usersCollection.findOneAndUpdate(
          { _id: telegramId },
          { $inc: { balance: amount } },
          { returnNewDocument: true }
        );

        await paymentsCollection.updateOne(
          { _id: paymentId },
          { $set: { status: "confirmed" } }
        );

        return {
          success: true,
          status: "confirmed",
          new_balance: updatedUser.balance,
          message: `Payment confirmed! Balance topped up by ${amount} ₽.`
        };
      } else if (paymentInfo.status === "canceled") {
         await paymentsCollection.updateOne(
          { _id: paymentId },
          { $set: { status: "canceled" } }
        );

        return {
           success: false,
           status: "canceled",
           message: "Payment was canceled."
        };
      } else {
        return {
          success: false,
          status: paymentInfo.status,
          message: `Payment status is ${paymentInfo.status}.`
        };
      }
    } else {
      console.error(`Yookassa Get Payment Error: Status ${response.statusCode}`, response.body.text());
      throw new Error(`Failed to check payment status: ${response.statusCode}`);
    }
  } catch (err) {
    console.error("Error checking Yookassa payment status", err);
    throw err;
  }
};
