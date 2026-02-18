exports = async function() {
  // Hardcoded periods from original bot logic
  const SUBSCRIPTION_PERIODS = {
    '1_month': {'price': 50, 'days': 30, 'name': '1 Month'},
    '2_months': {'price': 90, 'days': 60, 'name': '2 Months'},
    '3_months': {'price': 120, 'days': 90, 'name': '3 Months'}
  };

  const configs = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");

  // Check availability for each period
  const result = [];
  for (const [key, value] of Object.entries(SUBSCRIPTION_PERIODS)) {
    const count = await configs.count({ period: key, used: false });
    result.push({
      id: key,
      ...value,
      available: count > 0,
      count: count // Optional: show how many left
    });
  }

  return result;
};
