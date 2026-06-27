import sqlite3
import os

db_path = "/Users/saeedanwar/Desktop/saeed/project/sla_guard/data/customer_accounts.db"

# Ensure directory exists
os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create Tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    tier TEXT NOT NULL CHECK(tier IN ('Bronze', 'Silver', 'Gold', 'Enterprise'))
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    plan_name TEXT NOT NULL,
    sla_uptime_percent REAL NOT NULL,
    max_monthly_refund_cap REAL NOT NULL,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    issue_type TEXT NOT NULL,
    requested_refund REAL NOT NULL,
    approved_refund REAL NOT NULL,
    date TEXT NOT NULL,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
)
""")

# Insert Mock Data
mock_customers = [
    (1, "Alice Vance", "alice@company-a.com", "Enterprise"),
    (2, "Bob Miller", "bob@startup-b.io", "Gold"),
    (3, "Charlie Davis", "charlie@freelancer-c.net", "Silver"),
    (4, "Diana Smith", "diana@personal-d.com", "Bronze")
]

mock_subscriptions = [
    (1, 1, "Enterprise Dedicated Cluster", 99.99, 1000.00),
    (2, 2, "Gold Multi-Tenant Pro", 99.90, 200.00),
    (3, 3, "Silver Developer Starter", 99.50, 50.00),
    (4, 4, "Bronze Free Hobby Plan", 99.00, 0.00)
]

mock_tickets = [
    (1, 1, "Database Server Outage", 500.00, 500.00, "2026-05-15"),
    (2, 2, "API Gateway Timeout", 100.00, 100.00, "2026-06-01"),
    (3, 3, "SSL Cert Expiry Downtime", 50.00, 25.00, "2026-06-10")
]

cursor.executemany("INSERT OR REPLACE INTO customers VALUES (?, ?, ?, ?)", mock_customers)
cursor.executemany("INSERT OR REPLACE INTO subscriptions VALUES (?, ?, ?, ?, ?)", mock_subscriptions)
cursor.executemany("INSERT OR REPLACE INTO tickets_history VALUES (?, ?, ?, ?, ?, ?)", mock_tickets)

conn.commit()
conn.close()

print(f"Mock SQLite database setup completed successfully at: {db_path}")
