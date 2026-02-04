# MongoDB Schema Design

## Collection: `users`
Stores user profile, balance, and subscription data.

```json
{
  "_id": "string (Telegram User ID)",
  "username": "string",
  "first_name": "string",
  "balance": "number (Decimal128 or Double)",
  "subscription_end": "date (ISO Date)",
  "referred_by": "string (Referrer User ID)",
  "referrals_count": "number",
  "created_at": "date",
  "used_configs": [
    {
      "config_name": "string",
      "config_link": "string",
      "period": "string",
      "issue_date": "date"
    }
  ]
}
```

## Collection: `configs`
Stores the pool of VPN configurations available for purchase.

```json
{
  "_id": "objectId",
  "period": "string (e.g., '1_month', '3_months')",
  "name": "string",
  "link": "string (VLESS/Trojan URL)",
  "code": "string (optional)",
  "used": "boolean",
  "assigned_to": "string (User ID, optional)",
  "created_at": "date"
}
```

## Collection: `payments`
Stores payment history.

```json
{
  "_id": "string (UUID)",
  "user_id": "string",
  "amount": "number",
  "status": "string ('pending', 'succeeded', 'canceled')",
  "provider_payment_id": "string",
  "type": "string ('topup', 'subscription')",
  "created_at": "date",
  "updated_at": "date"
}
```
