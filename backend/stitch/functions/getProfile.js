exports = async function() {
  const userId = context.user.id;
  const mongodb = context.services.get("mongodb-atlas");
  const usersCollection = mongodb.db("vpn").collection("users");

  const user = await usersCollection.findOne({ _id: userId });

  if (!user) {
    throw new Error("User not found");
  }

  let subscription_status = "❌ Нет активной подписки";
  let days_left = 0;

  if (user.subscription_end) {
      const end_date = new Date(user.subscription_end);
      const now = new Date();
      if (end_date > now) {
          days_left = Math.ceil((end_date - now) / (1000 * 60 * 60 * 24));
          const dateStr = end_date.toLocaleDateString('ru-RU');
          subscription_status = `✅ Активна еще ${days_left} дней (до ${dateStr})`;
      }
  }

  return {
      balance: user.balance || 0,
      first_name: user.first_name || "N/A",
      username: user.username || "N/A",
      subscription_status: subscription_status,
      days_left: days_left,
      referrals_count: user.referrals_count || 0,
      used_configs: user.used_configs || []
  };
};
