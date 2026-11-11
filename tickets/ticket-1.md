# Ticket 1 — Checkout with an empty cart returns 500

**Type:** bug · **Priority:** high · **Reported by:** frontend team

## Description

When a user clicks "Checkout" with an empty cart, the frontend sends an order
without items and the service answers with **500 Internal Server Error**.
The frontend shows "Something went wrong" and our error monitoring gets
flooded.

## Steps to reproduce

```bash
curl -i -X POST http://localhost:8080/orders \
     -H "Content-Type: application/json" \
     -d '{"items": []}'
```

The same happens when the `items` field is missing completely: `-d '{}'`.

## Expected behaviour

The client sent an invalid request, so the service should answer
**400 Bad Request** in our standard error format with a message that explains
what is wrong, for example:

```json
{ "status": 400, "error": "items: must not be empty" }
```

## Acceptance criteria

- `POST /orders` with `"items": []` → `400` with a non-empty `error` message.
- `POST /orders` without `items` → `400` with a non-empty `error` message.
- Valid orders are still created with `201`.
