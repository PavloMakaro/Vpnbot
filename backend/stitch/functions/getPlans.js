exports = async function(arg){
  // You can fetch this from a collection or keep it static
  const plans = context.services.get("mongodb-atlas").db("vpn_bot").collection("plans");
  const plansList = await plans.find({}).toArray();

  if (plansList.length === 0) {
    // Fallback if no plans in DB
    return [
      { _id: "1_month", days: 30, price: 50, name: "1 Month" },
      { _id: "2_months", days: 60, price: 90, name: "2 Months" },
      { _id: "3_months", days: 90, price: 120, name: "3 Months" }
    ];
  }

  return plansList;
};
