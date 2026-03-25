-- КАТЕГОРИИ 
CREATE TABLE IF NOT EXISTS categories (
    id    SERIAL PRIMARY KEY,
    name  VARCHAR(100) NOT NULL,
    slug  VARCHAR(100) UNIQUE
);

-- ПОЛЬЗОВАТЕЛИ
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    full_name     VARCHAR(255) NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    phone         VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(50) DEFAULT 'customer',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- БУКЕТЫ
CREATE TABLE IF NOT EXISTS bouquets (
    id          SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id),
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    price       DECIMAL(10, 2) NOT NULL,
    image_url   VARCHAR(500),
    stock       INTEGER DEFAULT 0,
    is_popular  BOOLEAN DEFAULT FALSE
);

-- ЗАКАЗЫ
CREATE TABLE IF NOT EXISTS orders (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status           VARCHAR(50) DEFAULT 'new',
    total_amount     DECIMAL(10, 2),
    payment_method   VARCHAR(50),
    delivery_address TEXT,
    delivery_time    TIMESTAMP,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- СОСТАВ ЗАКАЗА
CREATE TABLE IF NOT EXISTS order_items (
    id         SERIAL PRIMARY KEY,
    order_id   INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    bouquet_id INTEGER REFERENCES bouquets(id),
    quantity   INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal   DECIMAL(10, 2) NOT NULL
);

-- КОРЗИНА
CREATE TABLE IF NOT EXISTS cart_items (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
    bouquet_id INTEGER REFERENCES bouquets(id) ON DELETE CASCADE,
    quantity   INTEGER NOT NULL DEFAULT 1,
    added_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, bouquet_id)
);

-- ИНДЕКСЫ
CREATE INDEX IF NOT EXISTS idx_orders_user_id    ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status     ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_cart_user_id      ON cart_items(user_id);

-- ТЕСТОВЫЕ ДАННЫЕ
INSERT INTO categories (name, slug) VALUES
('Розы', 'roses'),
('Тюльпаны', 'tulips'),
('Микс', 'mix');

INSERT INTO users (full_name, email, phone, password_hash, role) VALUES
('Иван Иванов', 'ivan@example.com', '79991234567', '$2b$12$test_hash', 'customer'),
('Админ', 'admin@example.com', '79990000000', '$2b$12$admin_hash', 'admin'),
('Мария Петрова', 'maria@example.com', '79997654321', '$2b$12$test_hash', 'customer');

INSERT INTO bouquets (category_id, name, description, price, image_url, stock, is_popular) VALUES
(1, 'Красные розы', '15 красных роз премиум', 2500.00, '/images/roses.jpg', 15, TRUE),
(2, 'Белые тюльпаны', '20 белых тюльпан', 1800.00, "C:\Users\Sony\Pictures\2464_1.jpg", 25, FALSE),
(3, 'Любимая', 'Микс роз + хризантемы', 4500.00, '/images/mix.jpg', 8, TRUE),
(1, 'Полярные розы', '10 полярных роз', 3200.00, '/images/polar.jpg', 12, FALSE);

INSERT INTO orders (user_id, status, total_amount, payment_method, delivery_address) VALUES
(1, 'paid', 4300.00, 'card', 'Москва, ул. Ленина 10');

INSERT INTO order_items (order_id, bouquet_id, quantity, unit_price, subtotal) VALUES
(1, 1, 1, 2500.00, 2500.00),
(1, 2, 1, 1800.00, 1800.00);
