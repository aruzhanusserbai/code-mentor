# Reference solution

The bug-free reference solution = `template/` + the reference patches below,
applied in order. The eval applies seeded-bug patches on top of it.

| Patch | Ticket | Change |
|-------|--------|--------|
| `ticket-0.patch` | 0 | Adds `GET /products/{id}` with `ProductNotFoundException` → 404 |
| `ticket-1.patch` | 1 | Adds `@NotEmpty` to `CreateOrderRequest.items` → 400 for `[]` and missing items |
| `ticket-2.patch` | 2 | Assigns the result of `BigDecimal.add` in `OrderService.create` → total counts all items |

Build the reference solution in a copy of the template:

```bash
cp -r template /tmp/reference
cd /tmp/reference
git apply ../path/to/codementor/eval/reference/ticket-0.patch
git apply ../path/to/codementor/eval/reference/ticket-1.patch
git apply ../path/to/codementor/eval/reference/ticket-2.patch
```

Patch paths are relative to `template/`. From the repository root you can
check them with `git apply --check --directory=template eval/reference/ticket-0.patch`.

Verified on 18 Nov 2026 in Docker: with all three patches applied, all tests
in `tests/tickets/ticket_0`, `ticket_1` and `ticket_2` pass (11 passed); on the
untouched template, the ticket 0, 1 and 2 tests fail (7 failed, 4 passed: the
tests of behaviour that already works, e.g. health and single-item orders).
