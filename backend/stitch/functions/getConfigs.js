exports = function() {
  // Hardcoded or fetched from DB
  // Typically these are static but can be in a 'configs_meta' collection
  return {
    '1_month': { price: 50, days: 30, label: "1 Месяц" },
    '2_months': { price: 90, days: 60, label: "2 Месяца" },
    '3_months': { price: 120, days: 90, label: "3 Месяца" }
  };
};
