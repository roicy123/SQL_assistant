"""Generate a small synthetic sales database (sales.db). Deterministic: same data every run."""
import datetime as dt
import os
import random
import sqlite3

DB_PATH = os.getenv("SALES_DB", "sales.db")
random.seed(7)

FIRST = ["Aarav", "Meera", "Rohan", "Anjali", "Vikram", "Diya", "Arjun", "Kavya", "Nikhil", "Priya",
         "Rahul", "Sneha", "Karthik", "Isha", "Aditya", "Neha", "Siddharth", "Pooja", "Varun", "Lakshmi"]
LAST = ["Nair", "Menon"]
CITIES = ["Kochi", "Mumbai", "Bengaluru", "Chennai", "Delhi", "Pune"]
PRODUCTS = [
    ("Wireless Mouse", "Electronics", 899), ("Bluetooth Speaker", "Electronics", 2499),
    ("USB-C Hub", "Electronics", 1599), ("Webcam", "Electronics", 3299),
    ("Desk Lamp", "Home", 1199), ("Water Bottle", "Home", 499),
    ("Office Chair", "Home", 7999), ("Notebook Set", "Home", 349),
    ("Yoga Mat", "Fitness", 999), ("Dumbbell Set", "Fitness", 2999),
    ("Resistance Bands", "Fitness", 599), ("Skipping Rope", "Fitness", 299),
]
NEVER_SOLD = "Skipping Rope"          # deliberately never ordered (used by an evaluation question)
NO_ORDER_CUSTOMERS = 5                # the last 5 customers never place an order (used by an evaluation question)

SCHEMA = """
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT NOT NULL,
    signup_date TEXT NOT NULL          -- YYYY-MM-DD
);
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    category   TEXT NOT NULL,
    price      REAL NOT NULL
);
CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date  TEXT NOT NULL,         -- YYYY-MM-DD
    status      TEXT NOT NULL          -- completed | cancelled | returned
);
CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders(order_id),
    product_id    INTEGER NOT NULL REFERENCES products(product_id),
    quantity      INTEGER NOT NULL,
    unit_price    REAL NOT NULL
);
"""


def rand_date(start, end):
    return start + dt.timedelta(days=random.randint(0, (end - start).days))


def build(path=DB_PATH):
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)

    customers = []
    for i in range(40):
        name = f"{FIRST[i % 20]} {LAST[i // 20]}"
        city = CITIES[i % len(CITIES)] if i < 30 else random.choice(CITIES)
        signup = rand_date(dt.date(2024, 1, 1), dt.date(2025, 6, 30)).isoformat()
        customers.append((i + 1, name, city, signup))
    conn.executemany("INSERT INTO customers VALUES (?,?,?,?)", customers)
    conn.executemany("INSERT INTO products VALUES (?,?,?,?)",
                     [(i + 1, n, c, p) for i, (n, c, p) in enumerate(PRODUCTS)])

    sellable = [(i + 1, p) for i, (n, c, p) in enumerate(PRODUCTS) if n != NEVER_SOLD]
    active_customers = 40 - NO_ORDER_CUSTOMERS
    item_id = 1
    for order_id in range(1, 321):
        status = random.choices(["completed", "cancelled", "returned"], weights=[80, 12, 8])[0]
        conn.execute("INSERT INTO orders VALUES (?,?,?,?)",
                     (order_id, random.randint(1, active_customers),
                      rand_date(dt.date(2025, 1, 1), dt.date(2025, 12, 31)).isoformat(), status))
        for _ in range(random.randint(1, 4)):
            pid, price = random.choice(sellable)
            conn.execute("INSERT INTO order_items VALUES (?,?,?,?,?)",
                         (item_id, order_id, pid, random.randint(1, 3), price))
            item_id += 1
    conn.commit()
    conn.close()
    print(f"Created {path}")


if __name__ == "__main__":
    build()