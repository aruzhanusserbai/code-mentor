# ShopFlow orders-service

Orders service for the ShopFlow online shop. Welcome to the team!

## Run

Requirements: Docker with Docker Compose.

```bash
docker compose up --build
```

The service listens on `http://localhost:8080`, PostgreSQL on `localhost:5432`
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
2. Create a branch: `git checkout -b ticket-1`.
3. Fix it, commit, push and open a pull request.
4. Automated checks run on the PR, and the mentor bot comments with hints.
