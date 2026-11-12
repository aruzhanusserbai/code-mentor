# Ticket 0 — Set up your workplace: product details endpoint

**Type:** task · **Priority:** normal

## Context

Welcome to the team! This first ticket helps you get the project running and
go through the full pull request flow once.

The frontend team is building a product page and needs to load **one product
by its id**. Right now we only have `GET /products`, which returns everything.

## What to do

1. Run the project locally (see `README.md`) and check that
   `GET /actuator/health` returns `UP`.
2. Add the endpoint `GET /products/{id}`:
   - returns the product in the same format as one element of `GET /products`;
   - returns `404` in our standard error format if the product does not exist.
3. Create a branch named `ticket-0-<short-description>`, for example
   `ticket-0-product-by-id`. Commit, push and open a pull request.
   The automated checks find the ticket by the branch name, so the
   `ticket-0-` prefix is required.

## Acceptance criteria

- `GET /products/1` → `200` with the product.
- `GET /products/999999` → `404` with body `{ "status": 404, "error": "..." }`.
- The rest of the API keeps working as described in `CONTRACT.md`.

## Tip

We already have a very similar endpoint for orders. Look at how it is done
and follow the same style.
