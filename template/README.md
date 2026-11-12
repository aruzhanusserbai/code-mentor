# ShopFlow orders-service

Orders service for the ShopFlow online shop. Welcome to the team!

## Run

Requirements: Docker with Docker Compose.

```bash
docker compose up --build
```

The service listens on `http://localhost:8080`, PostgreSQL on `localhost:5433`
(database / user / password: `orders`).

Check that it works:

```bash
curl http://localhost:8080/actuator/health
curl http://localhost:8080/products
```

## Code map

```
src/main/java/com/shopflow/orders/
├── product/   products: entity, repository, service, controller
├── order/     orders: entity, repository, service, controller, dto/
└── common/    exceptions and the global error handler
src/main/resources/
├── application.yml
└── db/migration/   Flyway migrations (schema + seed data)
```

The API is described in [CONTRACT.md](CONTRACT.md).

## Work process

1. Pick a ticket from the `tickets/` folder.
2. Create a branch named `ticket-<N>-<short-description>`, for example
   `git checkout -b ticket-1-empty-cart`. Lowercase letters, digits and `-` only.
3. Fix it, commit, push and open a pull request.
4. Automated checks run the tests **for ticket N only** (taken from the branch
   name), and the mentor bot comments with hints. A PR from a branch that does
   not follow the naming rule is not checked: the check fails with a message
   asking you to rename the branch.
