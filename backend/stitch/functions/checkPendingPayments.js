exports = async function() {
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const paymentsCollection = db.collection("payments");

  const pendingPayments = await paymentsCollection.find({ status: "pending", method: "yookassa_smart" }).toArray();

  for (const payment of pendingPayments) {
    try {
      await context.functions.execute("checkPayment", payment._id);
    } catch (e) {
      console.error(`Error checking payment ${payment._id}: ${e}`);
    }
  }

  return { success: true, count: pendingPayments.length };
};