exports = async function(userInfo) {
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("users");
  const userId = context.user.id; // String ID from auth, guaranteed to be Telegram ID

  if (!userId) {
      throw new Error("User must be authenticated");
  }

  // Try to find user
  let user = await collection.findOne({ _id: userId });

  if (!user) {
    // New User Logic
    console.log("Creating new user:", userId);
    const now = new Date();
    user = {
      _id: userId,
      username: userInfo.username || "",
      first_name: userInfo.first_name || "",
      balance: 50, // Welcome bonus
      subscription_end: null,
      referrals_count: 0,
      used_configs: [],
      created_at: now
    };

    // Handle Referral
    if (userInfo.start_param) {
      const referrerId = userInfo.start_param.toString();
      // Prevent self-referral
      if (referrerId !== userId) {
        const referrer = await collection.findOne({ _id: referrerId });
        if (referrer) {
          console.log("Processing referral from:", referrerId);

          // Calculate new subscription end date for referrer
          let currentEnd = referrer.subscription_end ? new Date(referrer.subscription_end) : new Date();
          if (currentEnd < new Date()) {
              currentEnd = new Date();
          }
          currentEnd.setDate(currentEnd.getDate() + 7); // Add 7 days bonus

          // Bonus for referrer
          await collection.updateOne(
            { _id: referrerId },
            {
              $inc: { balance: 25, referrals_count: 1 },
              $set: { subscription_end: currentEnd }
            }
          );
          user.referred_by = referrerId;
        }
      }
    }

    await collection.insertOne(user);
  } else {
    // Update basic info if changed
    if (userInfo.username && userInfo.username !== user.username) {
       await collection.updateOne({ _id: userId }, { $set: { username: userInfo.username } });
       user.username = userInfo.username;
    }
    if (userInfo.first_name && userInfo.first_name !== user.first_name) {
       await collection.updateOne({ _id: userId }, { $set: { first_name: userInfo.first_name } });
       user.first_name = userInfo.first_name;
    }
  }

  return user;
};
