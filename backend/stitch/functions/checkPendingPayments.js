exports = async function() {
  const telegramId = context.user.identities[0].id;
  const db = context.services.get("mongodb-atlas").db("vpn_bot");

  const pendingPayments = await db.collection("payments").find({
    user_id: telegramId,
    status: "pending"
  }).toArray();

  if (!pendingPayments || pendingPayments.length === 0) {
    return { success: true, processed: 0, messages: [] };
  }

  let processed = 0;
  let messages = [];

  for (const payment of pendingPayments) {
    try {
      const result = await context.functions.execute("checkPayment", payment._id);

      if (result.success && result.status === "confirmed") {
        messages.push(`Balance top-up successful: +${result.amount} RUB.`);
        processed++;
      } else if (result.success && result.status === "canceled") {
        messages.push(`Payment canceled: ${payment._id}`);
        processed++;
      }
    } catch (e) {
      console.error(`Error verifying payment ${payment._id}: ${e}`);
    }
  }

  return { success: true, processed, messages };
};