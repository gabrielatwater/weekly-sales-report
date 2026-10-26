"""Version 2: the weekly report plus a plain-English summary.

Run it:  python3 report_v2.py
"""
from report import load_orders, split_weeks, summarize, build_report
from ai_summary import ai_summary_with_fallback

# This one line decides who writes the summary. Swap in rule_based_summary
# (from summary.py) any time you want the no-AI version.
SUMMARIZER = ai_summary_with_fallback


def main():
    orders = load_orders("sales.csv")
    if not orders:
        print("sales.csv has no orders, so there is nothing to report.")
        return

    this_orders, last_orders, start, end = split_weeks(orders)
    this_week = summarize(this_orders)
    last_week = summarize(last_orders)

    report = build_report(this_week, last_week, start, end)
    report += "\nSummary:\n" + SUMMARIZER(this_week, last_week) + "\n"

    with open("weekly_report_v2.txt", "w") as f:
        f.write(report)

    print(report)
    print("Saved to weekly_report_v2.txt")


if __name__ == "__main__":
    main()
