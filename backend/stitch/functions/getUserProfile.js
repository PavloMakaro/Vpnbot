exports = async function() {
  const user = context.user;
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const doc = await collection.findOne({ telegram_id: user.id });

  if (!doc) {
    throw new Error("User not found");
  }

  // Mask sensitive data if needed, but for 'getUserProfile' intended for the user themselves, it's fine.
  // Add calculated fields if necessary (e.g. is_subscribed boolean)

  const now = new Date();
  const isSubscribed = doc.subscription_end && new Date(doc.subscription_end) > now;

  return {
    id: doc.telegram_id,
    first_name: doc.first_name,
    username: doc.username,
    balance: doc.balance || 0,
    subscription_end: doc.subscription_end,
    is_subscribed: isSubscribed,
    referral_count: doc.referral_count || 0,
    referral_earnings: doc.referral_earnings || 0,
    configs: doc.configs || [] // Or separate call
  };
};
