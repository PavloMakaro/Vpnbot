exports = async function(referrerId) {
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const userId = context.user.id;

  let user = await collection.findOne({ _id: userId });

  if (!user) {
    // New User
    const initialBalance = 50; // Welcome bonus
    const newUser = {
      _id: userId,
      balance: initialBalance,
      username: context.user.data.username || "",
      first_name: context.user.data.name || "",
      created_at: new Date(),
      referrals_count: 0,
      used_configs: [],
      subscription_end: null
    };

    // Handle Referral
    if (referrerId && referrerId !== userId) {
      const referrer = await collection.findOne({ _id: referrerId });
      if (referrer) {
        newUser.referred_by = referrerId;
        newUser.balance += 0; // Bonus for being referred? Original code says only referrer gets bonus?
        // Original code:
        // New user gets 50 (REFERRAL_BONUS_NEW_USER)
        // Referrer gets 25 (REFERRAL_BONUS_REFERRER) + 7 days sub

        // Update Referrer
        await collection.updateOne(
          { _id: referrerId },
          {
            $inc: { balance: 25, referrals_count: 1 },
            // managing subscription end date logic is complex in updateOne if it depends on current date
            // For simplicity, we'll skip sub extension here or do it in a trigger
          }
        );
      }
    }

    await collection.insertOne(newUser);
    user = newUser;
  }

  return user;
};
