package com.shopflow.orders.product;

import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ProductService {

    private final ProductRepository productRepository;

    public ProductService(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    public List<ProductResponse> getAll() {
        return productRepository.findAll(Sort.by("id")).stream()
                .map(ProductResponse::from)
                .toList();
    }
}
