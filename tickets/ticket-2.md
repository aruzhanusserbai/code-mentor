# Ticket 2 — Order total is wrong for orders with several items

**Type:** bug · **Priority:** critical · **Reported by:** finance team

## Description

During the weekly reconciliation we found orders whose `total` is lower than
the sum of their items. A customer ordered two mechanical keyboards and one
USB-C hub, but the order says the total is **64000.00 KZT** instead of
**76990.00 KZT**. The items in the order look correct: products, quantities
and unit prices are right, only the total is wrong.

Orders with a single product seem fine. We have not found a pattern yet for
orders with several products.

## Steps to reproduce

```bash
curl -i -X POST http://localhost:8080/orders \
     -H "Content-Type: application/json" \
     -d '{"items": [{"productId": 1, "quantity": 2}, {"productId": 3, "quantity": 1}]}'
```

Compare `total` in the answer with the `items` in the same answer.
`GET /orders/{id}` shows the same wrong total.

## Expected behaviour

As described in `CONTRACT.md`: `total` is the sum of `unitPrice * quantity`
over **all** items of the order. For the request above it is
`2 * 32000.00 + 1 * 12990.00 = 76990.00`.

## Acceptance criteria

- An order with several different products has the correct `total`.
- The same product in two lines of one order is counted in both lines.
- `GET /orders/{id}` returns the same correct `total`.
- Orders with a single product are still correct.

## Useful reading

Before you change anything, find the exact place where the wrong number
appears. A debugger is the fastest way to watch a value change step by step:
[Debug your first Java application](https://www.jetbrains.com/help/idea/debugging-your-first-java-application.html)
(IntelliJ IDEA documentation; other IDEs have the same features).

## Branch

Work in a branch named `ticket-2-<short-description>`,
for example `ticket-2-order-total`. The automated checks run the ticket 2 tests
only for branches with this prefix.
