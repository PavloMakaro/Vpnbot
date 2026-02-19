exports = async function() {
  const mongodb = context.services.get("mongodb-atlas");
  const settings = mongodb.db("vpn_bot").collection("settings");

  try {
    const pricing = await settings.findOne({ _id: "pricing" });
    if (pricing && pricing.periods) {
      return pricing.periods;
    }
  } catch (err) {
    console.error("Error fetching pricing from DB, using fallback:", err);
  }

  // Fallback to hardcoded values (matching ai_studio_code.py)
  return {
    "1_month": { "price": 50, "days": 30, "name": "1 Month" },
    "2_months": { "price": 90, "days": 60, "name": "2 Months" },
    "3_months": { "price": 120, "days": 90, "name": "3 Months" }
  };
};
