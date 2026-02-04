// MongoDB Atlas App Services (Stitch) Functions

/**
 * Function: getUser
 * Retrieves user data securely.
 */
exports.getUser = async function(arg) {
  // In Stitch, 'context.user' gives the authenticated user
  const user = context.user;
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");

  // Find user by their Telegram ID (stored in custom data or id)
  // Assuming auth provider maps Telegram ID to user.id or we pass it
  const telegramId = user.custom_data.telegram_id;

  let doc = await usersCollection.findOne({ _id: telegramId });

  if (!doc) {
    // Create new user if not exists
    doc = {
      _id: telegramId,
      balance: 0,
      subscription_end: null,
      referrals_count: 0,
      created_at: new Date()
    };
    await usersCollection.insertOne(doc);
  }

  return doc;
};

/**
 * Function: buySubscription
 * Handles purchase logic with transaction.
 */
exports.buySubscription = async function(period) {
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");
  const configsCollection = db.collection("configs");
  const user = context.user;
  const telegramId = user.custom_data.telegram_id;

  const PRICES = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };

  const plan = PRICES[period];
  if (!plan) throw new Error("Invalid period");

  // Start Transaction (if supported by cluster tier)
  const session = context.services.get("mongodb-atlas").startSession();

  try {
    session.startTransaction();

    // 1. Check Balance
    const userDoc = await usersCollection.findOne({ _id: telegramId }, { session });
    if (userDoc.balance < plan.price) {
      throw new Error("Insufficient funds");
    }

    // 2. Find Available Config
    const config = await configsCollection.findOne(
      { period: period, used: false },
      { session }
    );

    if (!config) {
      throw new Error("No configs available. Please contact support.");
    }

    // 3. Deduct Balance & Update Subscription
    let currentEnd = userDoc.subscription_end ? new Date(userDoc.subscription_end) : new Date();
    if (currentEnd < new Date()) currentEnd = new Date();
    currentEnd.setDate(currentEnd.getDate() + plan.days);

    await usersCollection.updateOne(
      { _id: telegramId },
      {
        $inc: { balance: -plan.price },
        $set: { subscription_end: currentEnd },
        $push: {
          used_configs: {
            config_name: config.name,
            config_link: config.link,
            period: period,
            issue_date: new Date()
          }
        }
      },
      { session }
    );

    // 4. Mark Config as Used
    await configsCollection.updateOne(
      { _id: config._id },
      { $set: { used: true, assigned_to: telegramId } },
      { session }
    );

    await session.commitTransaction();
    return { success: true, message: "Subscription activated", config: config };

  } catch (error) {
    await session.abortTransaction();
    throw error;
  } finally {
    session.endSession();
  }
};

/**
 * Function: getConfigs
 * Returns user's configs
 */
exports.getConfigs = async function() {
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");
  const user = context.user;
  const telegramId = user.custom_data.telegram_id;

  const doc = await usersCollection.findOne({ _id: telegramId });
  return doc ? (doc.used_configs || []) : [];
};

/**
 * HTTPS Endpoint: paymentWebhook
 * Called by Payment Provider (Yookassa)
 */
exports.paymentWebhook = async function(payload) {
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const usersCollection = db.collection("users");
  const paymentsCollection = db.collection("payments");

  const body = EJSON.parse(payload.body.text());
  const paymentObject = body.object;

  if (paymentObject.status === 'succeeded') {
    const paymentId = paymentObject.id;
    const userId = paymentObject.metadata.user_id;
    const amount = parseFloat(paymentObject.amount.value);

    // Check if processed
    const existing = await paymentsCollection.findOne({ _id: paymentId });
    if (existing && existing.status === 'succeeded') return { status: 200 };

    await paymentsCollection.updateOne(
        { _id: paymentId },
        {
            $set: {
                status: 'succeeded',
                user_id: userId,
                amount: amount,
                updated_at: new Date()
            }
        },
        { upsert: true }
    );

    await usersCollection.updateOne(
        { _id: userId },
        { $inc: { balance: amount } }
    );
  }

  return { status: 200 };
};
