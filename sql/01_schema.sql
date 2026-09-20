CREATE DATABASE IF NOT EXISTS procureflow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE procureflow;

CREATE TABLE IF NOT EXISTS materials (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    category VARCHAR(64) NOT NULL,
    unit VARCHAR(16) NOT NULL,
    safety_stock INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS inventory (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    material_id BIGINT NOT NULL,
    warehouse VARCHAR(64) NOT NULL,
    on_hand_qty INT NOT NULL DEFAULT 0,
    reserved_qty INT NOT NULL DEFAULT 0,
    available_qty INT GENERATED ALWAYS AS (on_hand_qty - reserved_qty) STORED,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_material_warehouse (material_id, warehouse),
    CONSTRAINT fk_inventory_material FOREIGN KEY (material_id) REFERENCES materials(id),
    CONSTRAINT ck_inventory_nonnegative CHECK (on_hand_qty >= 0 AND reserved_qty >= 0 AND reserved_qty <= on_hand_qty)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS suppliers (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    rating DECIMAL(3,2) NOT NULL DEFAULT 5.00,
    on_time_rate DECIMAL(5,2) NOT NULL DEFAULT 100.00,
    status ENUM('ACTIVE', 'SUSPENDED', 'BLACKLISTED') NOT NULL DEFAULT 'ACTIVE',
    contact_name VARCHAR(64),
    contact_phone VARCHAR(32),
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS supplier_quotes (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    supplier_id BIGINT NOT NULL,
    material_id BIGINT NOT NULL,
    min_qty INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(12,2) NOT NULL,
    lead_time_days INT NOT NULL,
    valid_until DATE NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_quote (supplier_id, material_id, min_qty),
    CONSTRAINT fk_quote_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    CONSTRAINT fk_quote_material FOREIGN KEY (material_id) REFERENCES materials(id),
    CONSTRAINT ck_quote_positive CHECK (min_qty > 0 AND unit_price > 0 AND lead_time_days >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS purchase_orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    po_no VARCHAR(32) NOT NULL UNIQUE,
    requester VARCHAR(64) NOT NULL,
    supplier_id BIGINT NOT NULL,
    status ENUM('PENDING_APPROVAL', 'APPROVED', 'SENT', 'PARTIALLY_RECEIVED', 'RECEIVED', 'CANCELLED') NOT NULL,
    total_amount DECIMAL(14,2) NOT NULL,
    expected_date DATE NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_po_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS purchase_order_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    purchase_order_id BIGINT NOT NULL,
    material_id BIGINT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    received_qty INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_item_order FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id),
    CONSTRAINT fk_item_material FOREIGN KEY (material_id) REFERENCES materials(id),
    CONSTRAINT ck_item_quantity CHECK (quantity > 0 AND received_qty >= 0 AND received_qty <= quantity)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    entity_type VARCHAR(32) NOT NULL,
    entity_id BIGINT NOT NULL,
    action VARCHAR(32) NOT NULL,
    operator_name VARCHAR(64) NOT NULL,
    detail VARCHAR(512),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_audit_entity (entity_type, entity_id)
) ENGINE=InnoDB;

