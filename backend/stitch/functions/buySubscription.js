exports = async function(period) {
  const user = context.user;
  if (!user || !user.custom_data) {
    throw new Error("Authentication failed.");
  }

  const userId = user.custom_data._id || user.id;

  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn_bot").collection("users");
  const configsCollection = mongodb.db("vpn_bot").collection("configs");

  // Get config data
  const configsData = await context.functions.execute("getConfigs");
  if (!configsData[period]) {
    throw new Error("Invalid subscription period.");
  }

  const { price, days } = configsData[period];

  // 1. Fetch user to check balance
  const userProfile = await usersCollection.findOne({ _id: userId });
  if (!userProfile) {
    throw new Error("User profile not found.");
  }

  if (userProfile.balance < price) {
    throw new Error(`Insufficient balance. Requires ${price} ₽, you have ${userProfile.balance} ₽.`);
  }

  // 2. Atomically find and reserve an unused config
  // Check if they already have one for this period to avoid duplicates, similar to legacy bot
  const existingConfig = userProfile.used_configs && userProfile.used_configs.find(c => c.period === period);

  let reservedConfig;

  if (existingConfig) {
      // Use existing config logic from legacy
      reservedConfig = {
          name: existingConfig.config_name,
          link: existingConfig.config_link,
          code: existingConfig.config_code
      };
  } else {
      // Find a new config
      reservedConfig = await configsCollection.findOneAndUpdate(
        { period: period, used: false },
        { $set: { used: true } },
        { returnNewDocument: true }
      );

      if (!reservedConfig) {
        throw new Error("No available configs for this period. Please contact support.");
      }
  }

  // 3. Update User Balance and Subscription End Date
  const now = new Date();
  let newEndDate = new Date();

  if (userProfile.subscription_end) {
    const currentEnd = new Date(userProfile.subscription_end);
    if (currentEnd > now) {
      // Add to existing
      newEndDate = new Date(currentEnd.getTime() + (days * 24 * 60 * 60 * 1000));
    } else {
      // Start from now
      newEndDate = new Date(now.getTime() + (days * 24 * 60 * 60 * 1000));
    }
  } else {
    // Start from now
    newEndDate = new Date(now.getTime() + (days * 24 * 60 * 60 * 1000));
  }

  // Format used config object
  const usedConfigObj = {
      config_name: reservedConfig.name,
      config_link: reservedConfig.link,
      config_code: reservedConfig.code,
      period: period,
      issue_date: new Date().toISOString(),
      user_name: `${userProfile.first_name || 'User'} (@${userProfile.username || 'user'})`
  };

  const updateOps = {
    $inc: { balance: -price },
    $set: { subscription_end: newEndDate }
  };

  // Only push if it's a new config
  if (!existingConfig) {
      updateOps.$push = { used_configs: usedConfigObj };
  }

  const result = await usersCollection.updateOne(
    { _id: userId },
    updateOps
  );

  if (result.modifiedCount === 0) {
    // Revert config reservation if user update fails (unlikely, but good practice)
    if (!existingConfig) {
        await configsCollection.updateOne(
          { _id: reservedConfig._id },
          { $set: { used: false } }
        );
    }
    throw new Error("Failed to process payment. Try again.");
  }

  return {
    success: true,
    message: "Subscription purchased successfully!",
    new_balance: userProfile.balance - price,
    subscription_end: newEndDate.toLocaleString(),
    config: {
        name: reservedConfig.name,
        link: reservedConfig.link,
        code: reservedConfig.code
    }
  };
};