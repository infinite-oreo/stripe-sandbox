# Stripe Mock Payment Server

A local Stripe API mock that lets you test payment flows without real credentials.
Switching to real Stripe requires only changing the base URL and API key.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│   ┌──────────────────────────────────────────────────────┐  │
│   │  React + Tailwind  (port 3000)                       │  │
│   │  CheckoutForm  │  PaymentResult  │  Dashboard        │  │
│   └───────────────────────┬──────────────────────────────┘  │
└───────────────────────────│─────────────────────────────────┘
                            │ HTTP / JSON
┌───────────────────────────▼─────────────────────────────────┐
│                   FastAPI  (port 8000)                       │
│   ┌────────────────────────────────────────────────────┐    │
│   │  routers/                                          │    │
│   │  payment_intents.py  refunds.py  webhooks.py       │    │
│   └──────────────────────┬─────────────────────────────┘    │
│   ┌──────────────────────▼─────────────────────────────┐    │
│   │  services/                                         │    │
│   │  card_validator  payment_processor  webhook_sender │    │
│   └──────────────────────┬─────────────────────────────┘    │
│   ┌──────────────────────▼─────────────────────────────┐    │
│   │  SQLite (stripe_mock.db)                           │    │
│   │  PaymentIntent  Refund  WebhookEndpoint  Delivery  │    │
│   └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │ async HTTP POST
               ┌────────────▼───────────┐
               │  Your Webhook Server   │
               └────────────────────────┘
```

## Quick Start

```bash
# Docker (recommended)
docker-compose up --build

# Manual
cd backend && pip install -r requirements.txt && uvicorn main:app --reload
cd frontend && npm install && npm run dev
```

Backend: http://localhost:8000  
Frontend: http://localhost:3000  
API docs: http://localhost:8000/docs

## Test Card Numbers

| Card Number          | Behavior                         |
|----------------------|----------------------------------|
| 4242424242424242     | Always succeeds                  |
| 4000000000000002     | Always declined                  |
| 4000000000009995     | Declined — insufficient funds    |
| 4000000000000069     | Declined — expired card          |
| 4000000000000127     | Declined — incorrect CVC         |
| 4000002500003155     | Requires 3D Secure auth          |
| 4000000000000077     | Succeeds with 3s delay           |

Use any valid expiry (≥ current year), CVC `123`.

## API Endpoints

### Payment Intents

```bash
# Create
curl -X POST http://localhost:8000/v1/payment_intents \
  -H "Content-Type: application/json" \
  -d '{"amount": 1000, "currency": "usd"}'

# Confirm
curl -X POST http://localhost:8000/v1/payment_intents/{id}/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "payment_method_data": {
      "type": "card",
      "card": {"number": "4242424242424242", "exp_month": 12, "exp_year": 2030, "cvc": "123"}
    }
  }'

# Get
curl http://localhost:8000/v1/payment_intents/{id}

# List
curl "http://localhost:8000/v1/payment_intents?limit=10&status=succeeded"

# Cancel
curl -X POST http://localhost:8000/v1/payment_intents/{id}/cancel

# 3DS authenticate
curl -X POST http://localhost:8000/v1/payment_intents/{id}/authenticate \
  -H "Content-Type: application/json" \
  -d '{"action": "success"}'
```

### Refunds

```bash
# Full refund
curl -X POST http://localhost:8000/v1/refunds \
  -H "Content-Type: application/json" \
  -d '{"payment_intent": "pi_mock_xxx"}'

# Partial refund
curl -X POST http://localhost:8000/v1/refunds \
  -H "Content-Type: application/json" \
  -d '{"payment_intent": "pi_mock_xxx", "amount": 500}'

# Get
curl http://localhost:8000/v1/refunds/{id}
```

### Webhooks

```bash
# Register (use httpbin for testing)
curl -X POST http://localhost:8000/v1/webhook_endpoints \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://httpbin.org/post",
    "events": ["payment_intent.succeeded", "payment_intent.payment_failed"]
  }'

# List
curl http://localhost:8000/v1/webhook_endpoints

# Delete
curl -X DELETE http://localhost:8000/v1/webhook_endpoints/{id}
```

Webhook payload format:
```json
{
  "id": "evt_mock_xxx",
  "type": "payment_intent.succeeded",
  "created": 1234567890,
  "data": { "object": { ...PaymentIntent... } }
}
```

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

## Migrating to Real Stripe

Only two changes needed:

1. **Base URL**: Change `http://localhost:8000` → `https://api.stripe.com`
2. **Authorization**: Add `Authorization: Bearer sk_live_xxx` header

The request/response shapes are interface-compatible with Stripe's API.
Your integration code needs zero modifications beyond those two config values.

```python
# Before (mock)
client = stripe.StripeClient("mock_key", base_url="http://localhost:8000")

# After (real)
client = stripe.StripeClient("sk_live_your_key")
```
