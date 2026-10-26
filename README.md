# Weekly Sales Report Automation

A Python tool that turns a raw sales CSV into a clear weekly report: revenue, orders, average order value, top products, and a plain-English summary of how this week compared to last week.

Small businesses often spend hours every week copying numbers into reports. This automates that. The summary is written by an AI (Groq's free API), and the tool falls back to a rule-based summary automatically if the AI is unavailable, so the report always gets produced.

## Sample output

```
WEEKLY SALES REPORT
Week: 2026-10-19 to 2026-10-25
========================================

Revenue:         $3,731.50  (+68.4% vs last week)
Orders:          88  (+57.1% vs last week)
Avg order value: $42.40  (+7.2% vs last week)

Top products by revenue:
  1. Pour-Over Kit: $1,482.00
  2. Espresso Beans 1kg: $1,008.00
  3. Gift Card: $675.00

Summary:
This week your revenue was $3,731.50, up 68.4% from last week. You processed
88 orders, a 57.1% increase, and the average order value rose to $42.40, up 7.2%.
The Pour-Over Kit generated the most revenue at $1,482.00 ...
```

(The data in this repo is generated sample data for a fictional coffee shop.)

## Features

- Reads sales data from a CSV file
- Compares the latest 7 days against the 7 days before
- Calculates revenue, order count, average order value, and top products
- AI-written summary through the Groq API, told to use only the supplied facts so it doesn't invent explanations
- Automatic fallback to a rule-based summary if the API key, package, or network is unavailable
- Handles edge cases such as no data for the previous week (no divide-by-zero crashes)

## How it works

```
sales.csv -> load_orders -> split_weeks -> summarize -> build_report
                                                     \-> summarizer (AI or rule-based) -> weekly_report_v2.txt
```

| File | Purpose |
|---|---|
| `make_sample_data.py` | Generates fake sales data (`sales.csv`) |
| `report.py` | Loads data, splits weeks, calculates the numbers, builds the report |
| `summary.py` | Rule-based summary writer (no AI, no key needed) |
| `ai_summary.py` | AI summary via Groq, with fallback to `summary.py` |
| `report_v2.py` | Runs everything and saves `weekly_report_v2.txt` |

The summarizer is a swappable function. Changing one line in `report_v2.py` switches between AI and rule-based summaries.

## Setup

Requires Python 3.9 or newer.

```bash
git clone https://github.com/gabrielatwater/weekly-sales-report.git
cd weekly-sales-report
python3 -m venv .venv
source .venv/bin/activate
pip install groq
```

Get a free API key at [console.groq.com/keys](https://console.groq.com/keys), then:

```bash
export GROQ_API_KEY="your-key-here"
```

## Usage

```bash
python3 make_sample_data.py   # optional: create fresh sample data
python3 report_v2.py          # generate the report
```

No API key? The report still runs and uses the rule-based summary.

To use a specific Groq model: `export GROQ_MODEL="model-name"`.

## Roadmap

- [x] Version 1: report from a CSV
- [x] Version 2: AI-written summary with fallback
- [ ] Version 3: run on a weekly schedule in AWS (Lambda, S3), defined with Terraform
- [ ] Version 4: read from a real data source and email the report

## What I learned

Working with CSV data and dictionaries in Python, structuring code into small reusable functions, calling an AI API and writing prompts that limit it to supplied facts, and building in fallbacks so automation fails gracefully.

## Author

Gabriel Atwater
