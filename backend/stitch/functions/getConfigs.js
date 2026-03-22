exports = async function() {
    const userId = context.user.identities[0].id;
    if (!userId) {
        throw new Error("Unauthorized");
    }

    // Hardcoded subscription periods matching legacy Python script
    return {
        '1_month': { 'price': 50, 'days': 30 },
        '2_months': { 'price': 90, 'days': 60 },
        '3_months': { 'price': 120, 'days': 90 }
    };
};
