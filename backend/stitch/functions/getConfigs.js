exports = async function() {
  // Get available subscription periods and prices
  // This matches the python code's SUBSCRIPTION_PERIODS

  const periods = {
    '1_month': {'price': 50, 'days': 30, 'name': '1 Month'},
    '2_months': {'price': 90, 'days': 60, 'name': '2 Months'},
    '3_months': {'price': 120, 'days': 90, 'name': '3 Months'}
  };

  // Optionally check if configs are available for each period
  const collection = context.services.get("mongodb-atlas").db("vpn_bot").collection("configs");

  const availability = {};
  for (const [key, value] of Object.entries(periods)) {
    const count = await collection.count({ period: key, used: false });
    availability[key] = {
      ...value,
      available: count > 0,
      count: count
    };
  }

  return availability;
};
