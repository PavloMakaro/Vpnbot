exports = async function() {
    // Return hardcoded subscription periods to match legacy implementation
    return {
        periods: {
            '1_month': { price: 50, days: 30 },
            '2_months': { price: 90, days: 60 },
            '3_months': { price: 120, days: 90 }
        }
    };
};