exports = async function() {
    // Return hardcoded periods, matching the original Python ai_studio_code.py logic
    // SUBSCRIPTION_PERIODS = {
    //     '1_month': {'price': 50, 'days': 30},
    //     '2_months': {'price': 90, 'days': 60},
    //     '3_months': {'price': 120, 'days': 90}
    // }

    return {
        '1_month': { 'price': 50, 'days': 30, 'label': '30 дней (50 ₽)' },
        '2_months': { 'price': 90, 'days': 60, 'label': '60 дней (90 ₽)' },
        '3_months': { 'price': 120, 'days': 90, 'label': '90 дней (120 ₽)' }
    };
};