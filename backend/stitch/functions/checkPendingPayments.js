exports = async function() {
  const telegramId = context.user.identities[0].id;
  if (!telegramId) {
    throw new Error("No Telegram ID found in context");
  }

  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const paymentsCollection = db.collection("payments");

  // Fetch pending payments for the current user
  const pendingPayments = await paymentsCollection.find({ user_id: telegramId, status: "pending" }).toArray();

  if (pendingPayments.length === 0) {
    return { success: true, message: "No pending payments." };
  }

  // Iterate and check status
  let checkedCount = 0;
  let successCount = 0;

  for (const payment of pendingPayments) {
    try {
      const result = await context.functions.execute("checkPayment", payment._id);
      if (result.success && result.message.includes("Balance topped up")) {
        successCount++;
      }
      checkedCount++;
    } catch (e) {
      console.log(`Error checking payment ${payment._id}: ${e}`);
    }
  }

  return {
    success: true,
    message: `Checked ${checkedCount} pending payments. Confirmed ${successCount}.`
  };
};
