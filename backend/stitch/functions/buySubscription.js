exports = async function(period) {
  const user_id = context.user.id;
  const db = context.services.get("mongodb-atlas").db("vpn_bot");
  const users = db.collection("users");
  const configs = db.collection("configs");
  const plans = db.collection("plans");

  let plan = await plans.findOne({ _id: period });

  if (!plan) {
    // Hardcoded fallback logic
    const periods = {
      '1_month': { price: 50, days: 30 },
      '2_months': { price: 90, days: 60 },
      '3_months': { price: 120, days: 90 }
    };
    if (periods[period]) {
        plan = { _id: period, ...periods[period] };
    } else {
        throw new Error("Plan not found: " + period);
    }
  }

  // 1. Check balance and deduct atomically
  // We first check if user has enough balance
  const user = await users.findOne({ _id: user_id });
  if (!user || user.balance < plan.price) {
     throw new Error("Insufficient balance");
  }

  // Optimistic locking or just atomic update
  const updateResult = await users.findOneAndUpdate(
    { _id: user_id, balance: { $gte: plan.price } },
    { $inc: { balance: -plan.price } },
    { returnNewDocument: true }
  );

  if (!updateResult) {
    throw new Error("Insufficient balance or concurrent transaction failed");
  }

  try {
    // 2. Find and assign config
    const config = await configs.findOneAndUpdate(
      { period: period, used: false },
      {
        $set: {
          used: true,
          assigned_to: user_id,
          assigned_at: new Date()
        }
      },
      { returnNewDocument: true }
    );

    if (!config) {
      throw new Error("No available configs for this period");
    }

    // 3. Update subscription end date
    let currentEnd = updateResult.subscription_end ? new Date(updateResult.subscription_end) : new Date();
    // If subscription already expired, start from now
    if (currentEnd < new Date()) {
        currentEnd = new Date();
    }

    const newEnd = new Date(currentEnd.getTime() + plan.days * 24 * 60 * 60 * 1000);

    // Update user with new subscription end date and add config to history
    await users.updateOne(
      { _id: user_id },
      {
        $set: { subscription_end: newEnd },
        $push: {
          used_configs: {
            config_id: config._id,
            name: config.name,
            period: period,
            assigned_at: new Date(),
            link: config.link,
            code: config.code
          }
        }
      }
    );

    return {
      success: true,
      new_end: newEnd,
      config: {
        name: config.name,
        link: config.link,
        code: config.code
      }
    };

  } catch (err) {
    // Refund on error
    await users.updateOne({ _id: user_id }, { $inc: { balance: plan.price } });
    throw new Error(err.message || "Purchase failed. Balance refunded.");
  }
};
