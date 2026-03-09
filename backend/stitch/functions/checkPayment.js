exports = async function(telegramId, paymentId) {
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const paymentsColl = db.collection("payments");
  const usersColl = db.collection("users");

  const paymentRecord = await paymentsColl.findOne({ _id: paymentId, user_id: telegramId });
  if (!paymentRecord) {
      return { success: false, message: "Payment not found." };
  }

  if (paymentRecord.status === "confirmed") {
      return { success: true, message: "Payment already confirmed." };
  }

  if (paymentRecord.status !== "pending") {
      return { success: false, message: `Payment is in status: ${paymentRecord.status}` };
  }

  const shopId = context.values.get("YOOKASSA_SHOP_ID");
  const secretKey = context.values.get("YOOKASSA_SECRET_KEY");
  const authString = Buffer.from(`${shopId}:${secretKey}`).toString("base64");

  try {
      const response = await context.http.get({
          url: `https://api.yookassa.ru/v3/payments/${paymentId}`,
          headers: {
              "Authorization": [`Basic ${authString}`]
          }
      });

      const responseBody = EJSON.parse(response.body.text());

      if (responseBody.status === "succeeded") {
          // Update payment status
          await paymentsColl.updateOne(
              { _id: paymentId },
              { $set: { status: "confirmed" } }
          );

          // Update user balance
          const amount = paymentRecord.amount;
          const user = await usersColl.findOne({ _id: telegramId });
          const newBalance = (user.balance || 0) + amount;

          await usersColl.updateOne(
              { _id: telegramId },
              { $set: { balance: newBalance } }
          );

          return { success: true, message: "Payment confirmed successfully.", new_balance: newBalance };
      } else if (responseBody.status === "canceled") {
          await paymentsColl.updateOne(
              { _id: paymentId },
              { $set: { status: "canceled" } }
          );
          return { success: false, message: "Payment was canceled." };
      } else {
          return { success: false, message: "Payment is still pending." };
      }

  } catch (error) {
      console.error("Yookassa Check Error:", error);
      return { success: false, message: "Error checking payment status." };
  }
};