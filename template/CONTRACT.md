# API contract — orders-service

This is the public contract of the service. Automated checks talk to the
service **only over HTTP** as described here, so you may restructure the code
however you like as long as the contract holds.

- Base URL: `http://localhost:8080`
- All request and response bodies are JSON (`Content-Type: application/json`).
- Money values are JSON numbers with 2 decimals (for example `32000.00`).

## Error format

Every error response (4xx and 5xx) has the same body:

```json
{ "status": 400, "error": "human-readable message" }
```

`status` equals the HTTP status code. `error` is a non-empty string.

## Endpoints

### `GET /actuator/health`

`200 OK` → `{ "status": "UP" }` when the service and the database are up.

### `GET /products`

`200 OK` → list of all products, ordered by `id`:

```json
[
  { "id": 1, "name": "Mechanical keyboard", "price": 32000.00, "currency": "KZT" }
]
```

### `GET /products/{id}`

- `200 OK` → one product, same shape as an element of `GET /products`.
- `404 Not Found` → product with this id does not exist (error format).

### `POST /orders`

Request:

```json
{
  "items": [
    { "productId": 1, "quantity": 2 },
    { "productId": 3, "quantity": 1 }
  ]
}
```

Rules:

- `items` is required and must contain at least one item.
- `productId` is required and must refer to an existing product.
- `quantity` is required and must be `>= 1`.
- All products in one order must have the same currency.

Responses:

- `201 Created` → the created order (see *Order* below).
  `status` is `"CREATED"`, `currency` is the products' currency,
  `total` is the sum of `unitPrice * quantity` over all items.
- `400 Bad Request` → any rule above is broken, or the body is missing or is
  not valid JSON (error format).

### `GET /orders/{id}`

- `200 OK` → the order.
- `404 Not Found` → order with this id does not exist (error format).
- `400 Bad Request` → `id` is not a number (error format).

### `GET /orders`

`200 OK` → list of all orders, ordered by `id`.

## Order

```json
{
  "id": 1,
  "status": "CREATED",
  "currency": "KZT",
  "total": 76990.00,
  "createdAt": "2026-11-11T10:15:30.123456Z",
  "items": [
    { "productId": 1, "productName": "Mechanical keyboard", "quantity": 2, "unitPrice": 32000.00 },
    { "productId": 3, "productName": "USB-C hub", "quantity": 1, "unitPrice": 12990.00 }
  ]
}
```

`unitPrice` is the product price at the moment the order was created.
