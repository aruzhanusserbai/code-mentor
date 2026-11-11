package com.shopflow.orders.order.dto;

import com.shopflow.orders.order.Order;
import com.shopflow.orders.order.OrderItem;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.List;

public record OrderResponse(
        Long id,
        String status,
        String currency,
        BigDecimal total,
        OffsetDateTime createdAt,
        List<Item> items
) {

    public record Item(Long productId, String productName, int quantity, BigDecimal unitPrice) {
    }

    public static OrderResponse from(Order order) {
        List<Item> items = order.getItems().stream()
                .map(OrderResponse::toItem)
                .toList();
        return new OrderResponse(order.getId(), order.getStatus(), order.getCurrency(),
                order.getTotal(), order.getCreatedAt(), items);
    }

    private static Item toItem(OrderItem item) {
        return new Item(item.getProduct().getId(), item.getProduct().getName(),
                item.getQuantity(), item.getUnitPrice());
    }
}
