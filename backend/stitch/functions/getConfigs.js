exports = async function() {
  // Hardcoded for now, could be a collection "products"
  const SUBSCRIPTION_PERIODS = {
    '1_month': {'price': 50, 'days': 30, 'name': '1 Month'},
    '2_months': {'price': 90, 'days': 60, 'name': '2 Months'},
    '3_months': {'price': 120, 'days': 90, 'name': '3 Months'}
  };

  return SUBSCRIPTION_PERIODS;
};
