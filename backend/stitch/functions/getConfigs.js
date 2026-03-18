exports = function() {
  // Subscription prices and periods are hardcoded here to match legacy bot behavior
  return {
    '1_month': { price: 50, days: 30 },
    '2_months': { price: 90, days: 60 },
    '3_months': { price: 120, days: 90 }
  };
};
