exports = async function(payload) {
  // This function handles webhook events from Yookassa.
  // Configure this function as a Webhook in Atlas App Services.
  // The 'payload' argument contains the request body.

  const body = EJSON.parse(payload.body.text());

  if (body.type === "notification" && body.event === "payment.succeeded") {
    const paymentObj = body.object;
    const paymentId = paymentObj.id;
    const amount = parseFloat(paymentObj.amount.value);
    const userId = paymentObj.metadata.user_id; // We stored this in metadata

    if (!userId) {
        console.error("No user_id in payment metadata");
        return; // Or throw error
    }

    const client = context.services.get("mongodb-atlas");
    const db = client.db("vpn_bot_db");
    const paymentsCollection = db.collection("payments");
    const usersCollection = db.collection("users");

    // Check if payment already processed to avoid double crediting
    const existingPayment = await paymentsCollection.findOne({ _id: paymentId });

    if (existingPayment && existingPayment.status === "succeeded") {
      console.log(`Payment ${paymentId} already processed.`);
      return { status: "already_processed" };
    }

    // Start session for transaction
    const session = client.startSession();
    try {
      session.startTransaction();

      // Update Payment Record
      await paymentsCollection.updateOne(
        { _id: paymentId },
        {
          $set: {
            status: "succeeded",
            completed_at: new Date(),
            raw_response: paymentObj
          }
        },
        { session }
      );

      // Update User Balance
      await usersCollection.updateOne(
        { _id: userId },
        { $inc: { balance: amount } },
        { session }
      );

      await session.commitTransaction();
      console.log(`Payment ${paymentId} processed successfully for user ${userId}.`);

    } catch (err) {
      await session.abortTransaction();
      console.error(`Transaction failed for payment ${paymentId}:`, err);
      throw err;
    } finally {
      session.endSession();
    }
  }

  return { status: "ok" };
};
