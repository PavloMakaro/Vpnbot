exports = async function() {
  const user = context.user;
  if (!user || !user.identities || user.identities.length === 0) {
    throw new Error("User not authenticated properly.");
  }

  // Extract custom identity ID which is the Telegram ID
  const telegramId = user.identities[0].id;

  const mongodb = context.services.get("mongodb-atlas");
  const paymentsCollection = mongodb.db("vpn_bot").collection("payments");

  // Fetch all pending payments for the current user
  const pendingPayments = await paymentsCollection.find({ user_id: telegramId, status: "pending" }).toArray();

  if (pendingPayments.length === 0) {
      return { success: true, message: "No pending payments found." };
  }

  let confirmedCount = 0;
  for (const payment of pendingPayments) {
      const result = await context.functions.execute("checkPayment", payment.payment_id);
      if (result.success) {
          confirmedCount++;
      }
  }

  return { success: true, message: `Checked ${pendingPayments.length} payments. Confirmed ${confirmedCount}.` };
};
