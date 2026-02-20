exports = async function(referrerId) {
  // referrerId is passed from the client (start_param)
  const userId = context.user.id;
  const users = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");

  // Check if user already exists
  const existingUser = await users.findOne({ _id: userId });
  if (existingUser) {
    return { status: "exists", user: existingUser };
  }

  const REFERRAL_BONUS_NEW_USER = 50;
  const REFERRAL_BONUS_REFERRER = 25;
  const REFERRAL_BONUS_DAYS = 7;

  // Create new user document
  const newUser = {
    _id: userId,
    balance: REFERRAL_BONUS_NEW_USER,
    subscription_end: null,
    referrals_count: 0,
    referred_by: null,
    used_configs: [],
    created_at: new Date()
  };

  // Handle Referral
  if (referrerId && referrerId !== userId) {
    const referrer = await users.findOne({ _id: referrerId });
    if (referrer) {
      newUser.referred_by = referrerId;

      // Update referrer
      let updateDoc = {
        $inc: { balance: REFERRAL_BONUS_REFERRER, referrals_count: 1 }
      };

      // Add bonus days to referrer
      let currentEnd = referrer.subscription_end ? new Date(referrer.subscription_end) : new Date();
      if (currentEnd < new Date()) {
          currentEnd = new Date();
      }
      currentEnd.setDate(currentEnd.getDate() + REFERRAL_BONUS_DAYS);
      updateDoc.$set = { subscription_end: currentEnd };

      await users.updateOne({ _id: referrerId }, updateDoc);
    }
  }

  await users.insertOne(newUser);
  return { status: "created", user: newUser };
};
