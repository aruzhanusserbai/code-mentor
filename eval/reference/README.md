# Reference solution

The bug-free reference solution = `template/` + the reference patches below,
applied in order. The eval applies seeded-bug patches on top of it.

| Patch | Ticket | Change |
|-------|--------|--------|
| `ticket-0.patch` | 0 | Adds `GET /products/{id}` with `ProductNotFoundException` → 404 |
| `ticket-1.patch` | 1 | Adds `@NotEmpty` to `CreateOrderRequest.items` → 400 for `[]` and missing items |

Build the reference solution in a copy of the template:

```bash
cp -r template /tmp/reference
cd /tmp/reference
git apply ../path/to/codementor/eval/reference/ticket-0.patch
git apply ../path/to/codementor/eval/reference/ticket-1.patch
```

Patch paths are relative to `template/`. From the repository root you can
check them with `git apply --check --directory=template eval/reference/ticket-0.patch`.

Verified on 11 Nov 2026: with both patches applied, all tests in
`tests/tickets/ticket_0` and `tests/tickets/ticket_1` pass; without them,
ticket 0 and ticket 1 tests fail.
