exports = async function() {
    // Return hardcoded subscription prices based on python legacy code
    return {
        '1_month': { price: 50, days: 30, title: '30 дней' },
        '2_months': { price: 90, days: 60, title: '60 дней' },
        '3_months': { price: 120, days: 90, title: '90 дней' }
    };
};
