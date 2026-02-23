exports = async function() {
  const mongodb = context.services.get("mongodb-atlas");
  const configsCollection = mongodb.db("vpn_bot").collection("configs");

  const subscriptionPeriods = {
    '1_month': { price: 50, days: 30, label: "1 Month" },
    '2_months': { price: 90, days: 60, label: "2 Months" },
    '3_months': { price: 120, days: 90, label: "3 Months" }
  };

  const availableCounts = await configsCollection.aggregate([
    { $match: { used: false } },
    { $group: { _id: "$period", count: { $sum: 1 } } }
  ]).toArray();

  const result = [];
  for (const [key, plan] of Object.entries(subscriptionPeriods)) {
    const availability = availableCounts.find(a => a._id === key);
    result.push({
      id: key,
      ...plan,
      available: availability ? availability.count : 0
    });
  }

  return result;
};
