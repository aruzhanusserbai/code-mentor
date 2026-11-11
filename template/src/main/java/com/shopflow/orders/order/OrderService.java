package com.shopflow.orders.order;

import com.shopflow.orders.common.InvalidOrderException;
import com.shopflow.orders.common.OrderNotFoundException;
import com.shopflow.orders.order.dto.CreateOrderRequest;
import com.shopflow.orders.order.dto.OrderItemRequest;
import com.shopflow.orders.order.dto.OrderResponse;
import com.shopflow.orders.product.Product;
import com.shopflow.orders.product.ProductRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.List;

@Service
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    private final OrderRepository orderRepository;
    private final ProductRepository productRepository;

    public OrderService(OrderRepository orderRepository, ProductRepository productRepository) {
        this.orderRepository = orderRepository;
        this.productRepository = productRepository;
    }

    @Transactional
    public OrderResponse create(CreateOrderRequest request) {
        Order order = new Order();
        order.setStatus("CREATED");
        order.setCreatedAt(OffsetDateTime.now());

        // one order = one currency, we take it from the first product
        Product firstProduct = findProduct(request.getItems().get(0).getProductId());
        order.setCurrency(firstProduct.getCurrency());

        BigDecimal total = BigDecimal.ZERO;
        for (OrderItemRequest itemRequest : request.getItems()) {
            Product product = findProduct(itemRequest.getProductId());
            if (!product.getCurrency().equals(order.getCurrency())) {
                throw new InvalidOrderException("All products in an order must have the same currency");
            }
            BigDecimal lineTotal = product.getPrice().multiply(BigDecimal.valueOf(itemRequest.getQuantity()));
            total = total.add(lineTotal);
            order.addItem(new OrderItem(product, itemRequest.getQuantity(), product.getPrice()));
        }
        order.setTotal(total);

        Order saved = orderRepository.save(order);
        log.info("Created order {} with {} items, total {} {}", saved.getId(), saved.getItems().size(),
                saved.getTotal(), saved.getCurrency());
        return OrderResponse.from(saved);
    }

    @Transactional(readOnly = true)
    public OrderResponse getById(Long id) {
        Order order = orderRepository.findById(id)
                .orElseThrow(() -> new OrderNotFoundException(id));
        return OrderResponse.from(order);
    }

    @Transactional(readOnly = true)
    public List<OrderResponse> getAll() {
        return orderRepository.findAll(Sort.by("id")).stream()
                .map(OrderResponse::from)
                .toList();
    }

    private Product findProduct(Long productId) {
        return productRepository.findById(productId)
                .orElseThrow(() -> new InvalidOrderException("Product " + productId + " does not exist"));
    }
}
