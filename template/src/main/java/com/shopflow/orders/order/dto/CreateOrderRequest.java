package com.shopflow.orders.order.dto;

import jakarta.validation.Valid;

import java.util.List;

public class CreateOrderRequest {

    @Valid
    private List<OrderItemRequest> items;

    public List<OrderItemRequest> getItems() {
        return items;
    }

    public void setItems(List<OrderItemRequest> items) {
        this.items = items;
    }
}
