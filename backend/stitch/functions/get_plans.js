exports = async function() {
  // Can be fetched from DB or hardcoded
  return [
    { id: "1_month", days: 30, price: 50 },
    { id: "2_months", days: 60, price: 90 },
    { id: "3_months", days: 90, price: 120 }
  ];
};
