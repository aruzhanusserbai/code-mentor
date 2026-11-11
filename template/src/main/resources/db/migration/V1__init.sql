CREATE TABLE products (
    id       BIGINT PRIMARY KEY,
    name     VARCHAR(255)   NOT NULL,
    price    NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3)     NOT NULL
);

CREATE TABLE orders (
    id         BIGSERIAL PRIMARY KEY,
    status     VARCHAR(32)    NOT NULL,
    currency   VARCHAR(3)     NOT NULL,
    total      NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMPTZ    NOT NULL
);

CREATE TABLE order_items (
    id         BIGSERIAL PRIMARY KEY,
    order_id   BIGINT         NOT NULL REFERENCES orders (id),
    product_id BIGINT         NOT NULL REFERENCES products (id),
    quantity   INT            NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL
);

CREATE INDEX idx_order_items_order_id ON order_items (order_id);
