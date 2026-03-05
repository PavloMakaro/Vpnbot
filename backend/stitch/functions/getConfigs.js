exports = async function() {
  // Hardcoded to match legacy bot behavior
  const SUBSCRIPTION_PERIODS = {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };
  return SUBSCRIPTION_PERIODS;
};