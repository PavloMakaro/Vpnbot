exports = async function() {
  const user = context.user;
  if (!user) {
    throw new Error("Unauthorized");
  }

  // Get Telegram ID from identities (Custom Function Auth)
  const identity = user.identities.find(id => id.provider_type === 'custom-function');
  const telegramId = identity ? identity.id : user.id;

  const usersCollection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  const doc = await usersCollection.findOne({ _id: telegramId });

  if (!doc) {
    return { balance: 0, subscription_end: null };
  }

  // Calculate active days
  let days_left = 0;
  if (doc.subscription_end) {
    const end = new Date(doc.subscription_end);
    const now = new Date();
    if (end > now) {
      const diff = end - now;
      days_left = Math.ceil(diff / (1000 * 60 * 60 * 24));
    }
  }

  return {
    balance: doc.balance || 0,
    subscription_end: doc.subscription_end,
    days_left: days_left,
    username: doc.username,
    first_name: doc.first_name,
    referrals_count: doc.referrals_count || 0
  };
};
