package com.shopflow.orders.common;

public class OrderNotFoundException extends RuntimeException {

    public OrderNotFoundException(Long id) {
        super("Order " + id + " not found");
    }
}
