"""Reads sales.csv and writes a weekly report comparing this week to last week.

Run it:  python3 report.py
"""
import csv
from collections import defaultdict
from datetime import datetime, timedelta


def load_orders(path):
    """Read the CSV file and return a list of orders (one dictionary per row)."""
    orders = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            orders.append({
                "order_id": row["order_id"],
                # Text like "2026-10-23" becomes a real date we can do math with
                "date": datetime.strptime(row["date"], "%Y-%m-%d").date(),
                "product": row["product"],
                "quantity": int(row["quantity"]),
                "unit_price": float(row["unit_price"]),
            })
    return orders


def summarize(orders):
    """Calculate the key numbers for a group of orders."""
    revenue = 0.0
    revenue_by_product = defaultdict(float)  # a dictionary that starts every value at 0.0

    for order in orders:
        line_total = order["quantity"] * order["unit_price"]
        revenue += line_total
        revenue_by_product[order["product"]] += line_total

    order_count = len(orders)
    average_order = revenue / order_count if order_count > 0 else 0.0

    # Sort products from highest revenue to lowest, keep the top 3
    top_products = sorted(
        revenue_by_product.items(), key=lambda item: item[1], reverse=True
    )[:3]

    return {
        "revenue": revenue,
        "order_count": order_count,
        "average_order": average_order,
        "top_products": top_products,
    }


def percent_change(new, old):
    """How much did a number change, as a percentage? Returns None if old is 0."""
    if old == 0:
        return None
    return (new - old) / old * 100


def format_change(new, old):
    """Turn a percent change into text like '+12.3%' for the report."""
    change = percent_change(new, old)
    if change is None:
        return "n/a"
    return f"{change:+.1f}%"


def build_report(this_week, last_week, start, end):
    """Put the numbers together into readable text."""
    lines = [
        "WEEKLY SALES REPORT",
        f"Week: {start} to {end}",
        "=" * 40,
        "",
        f"Revenue:         ${this_week['revenue']:,.2f}  "
        f"({format_change(this_week['revenue'], last_week['revenue'])} vs last week)",
        f"Orders:          {this_week['order_count']}  "
        f"({format_change(this_week['order_count'], last_week['order_count'])} vs last week)",
        f"Avg order value: ${this_week['average_order']:,.2f}  "
        f"({format_change(this_week['average_order'], last_week['average_order'])} vs last week)",
        "",
        "Top products by revenue:",
    ]
    for rank, (product, revenue) in enumerate(this_week["top_products"], start=1):
        lines.append(f"  {rank}. {product}: ${revenue:,.2f}")

    return "\n".join(lines) + "\n"


def split_weeks(orders):
    """Split orders into 'this week' and 'last week'.

    Returns (this_week_orders, last_week_orders, start_date, end_date).
    """
    # The "latest day" in the data decides which week is "this week"
    latest = max(order["date"] for order in orders)
    this_start = latest - timedelta(days=6)        # 7 days ending on the latest day
    last_start = latest - timedelta(days=13)       # the 7 days before that
    last_end = latest - timedelta(days=7)

    this_week_orders = [o for o in orders if this_start <= o["date"] <= latest]
    last_week_orders = [o for o in orders if last_start <= o["date"] <= last_end]
    return this_week_orders, last_week_orders, this_start, latest


def main():
    orders = load_orders("sales.csv")
    if not orders:
        print("sales.csv has no orders, so there is nothing to report.")
        return

    this_week_orders, last_week_orders, start, end = split_weeks(orders)

    report = build_report(
        summarize(this_week_orders),
        summarize(last_week_orders),
        start,
        end,
    )

    with open("weekly_report.txt", "w") as f:
        f.write(report)

    print(report)
    print("Saved to weekly_report.txt")


# This line means: only run main() when you run THIS file directly
# (python3 report.py). If another file imports report.py, main() stays quiet.
if __name__ == "__main__":
    main()
