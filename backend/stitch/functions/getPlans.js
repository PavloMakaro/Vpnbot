exports = function() {
  // Can fetch from DB or use hardcoded values from ai_studio_code.py
  return {
    '1_month': { name: '1 Month', price: 50, days: 30 },
    '2_months': { name: '2 Months', price: 90, days: 60 },
    '3_months': { name: '3 Months', price: 120, days: 90 }
  };
};
