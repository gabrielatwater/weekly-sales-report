"""Creates a fake sales.csv so we have data to practice on.

Run it once:  python3 make_sample_data.py
"""
import csv
import random
from datetime import date, timedelta

random.seed(42)  # makes the "random" numbers repeatable

# A small coffee shop's products and their prices
PRODUCTS = {
    "Espresso Beans 1kg": 24.00,
    "Cold Brew Bottle": 6.50,
    "Ceramic Mug": 12.00,
    "Pour-Over Kit": 38.00,
    "Gift Card": 25.00,
}

last_day = date.today()
first_day = last_day - timedelta(days=13)  # 14 days = two full weeks of data

rows = []
order_id = 1000
day = first_day

while day <= last_day:
    # The second week gets a few more orders per day, so the report shows growth
    is_second_week = day > first_day + timedelta(days=6)
    low, high = (8, 16) if is_second_week else (6, 13)

    for _ in range(random.randint(low, high)):
        product = random.choice(list(PRODUCTS))
        rows.append({
            "order_id": order_id,
            "date": day.isoformat(),  # looks like 2026-10-23
            "product": product,
            "quantity": random.randint(1, 3),
            "unit_price": PRODUCTS[product],
        })
        order_id += 1

    day += timedelta(days=1)

with open("sales.csv", "w", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=["order_id", "date", "product", "quantity", "unit_price"]
    )
    writer.writeheader()
    writer.writerows(rows)

print(f"Created sales.csv with {len(rows)} orders from {first_day} to {last_day}.")
