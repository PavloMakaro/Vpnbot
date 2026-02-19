# MongoDB Schema Design for VPN TMA

## Collection: `users`
Stores user profile, balance, and subscription status.

```json
{
  "_id": "String (Telegram User ID)",
  "username": "String",
  "first_name": "String",
  "balance": "Number (Float)",
  "subscription_end": "Date (ISO)",
  "referrals_count": "Number (Integer)",
  "referred_by": "String (Telegram User ID of referrer)",
  "created_at": "Date"
}
```

## Collection: `configs`
Stores the pool of VPN configurations available for assignment.

```json
{
  "_id": "ObjectId",
  "period": "String ('1_month', '2_months', '3_months')",
  "link": "String (vless://... or other protocol)",
  "code": "String (optional code if needed)",
  "name": "String (Display name)",
  "used": "Boolean (false by default)",
  "assigned_to": "String (Telegram User ID, if used)",
  "assigned_at": "Date (if used)"
}
```

## Collection: `payments`
Stores payment history and status.

```json
{
  "_id": "ObjectId",
  "user_id": "String (Telegram User ID)",
  "amount": "Number",
  "currency": "String ('RUB')",
  "status": "String ('pending', 'succeeded', 'canceled')",
  "yookassa_id": "String (External ID from Payment Provider)",
  "created_at": "Date",
  "updated_at": "Date"
}
```

## Collection: `settings`
Stores dynamic configuration like pricing.
Document ID: `pricing`

```json
{
  "_id": "pricing",
  "periods": {
    "1_month": { "price": 50, "days": 30 },
    "2_months": { "price": 90, "days": 60 },
    "3_months": { "price": 120, "days": 90 }
  },
  "referral": {
    "new_user_bonus": 50,
    "referrer_bonus": 25,
    "referrer_days": 7
  }
}
```
