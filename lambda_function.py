"""AWS Lambda entry point: builds the weekly report in the cloud.

What happens each time this runs:
  1. Download input/sales.csv from the S3 bucket
  2. Calculate the weekly numbers (same code as the local version)
  3. Write the report to reports/weekly_report_<date>.txt in the same bucket
"""
import os

import boto3

from ai_summary import ai_summary_with_fallback
from report import build_report, load_orders, split_weeks, summarize

INPUT_KEY = "input/sales.csv"
LOCAL_CSV = "/tmp/sales.csv"  # Lambda can only write files under /tmp

# Created once and reused if Lambda keeps the container warm
s3 = boto3.client("s3")
ssm = boto3.client("ssm")


def load_groq_key():
    """Fetch the Groq API key from AWS Parameter Store, if one is configured.

    The key is never in our code or in Terraform. It lives encrypted in
    Parameter Store, and only this function's IAM role may read it. We put it
    into the environment variable that ai_summary.py already looks for.
    """
    name = os.environ.get("GROQ_PARAMETER_NAME")
    if not name or os.environ.get("GROQ_API_KEY"):
        return  # nothing configured, or already loaded on an earlier run
    try:
        response = ssm.get_parameter(Name=name, WithDecryption=True)
        os.environ["GROQ_API_KEY"] = response["Parameter"]["Value"]
    except Exception as error:
        # Not fatal: the report falls back to the rule-based summary
        print(f"Could not load the Groq key from Parameter Store: {error}")


def handler(event, context):
    """Lambda calls this function. 'event' and 'context' come from AWS."""
    bucket = os.environ["BUCKET_NAME"]
    load_groq_key()

    s3.download_file(bucket, INPUT_KEY, LOCAL_CSV)
    orders = load_orders(LOCAL_CSV)
    if not orders:
        print("sales.csv has no orders, so there is nothing to report.")
        return {"status": "no data"}

    this_orders, last_orders, start, end = split_weeks(orders)
    this_week = summarize(this_orders)
    last_week = summarize(last_orders)

    report = build_report(this_week, last_week, start, end)
    report += "\nSummary:\n" + ai_summary_with_fallback(this_week, last_week) + "\n"

    report_key = f"reports/weekly_report_{end}.txt"
    s3.put_object(
        Bucket=bucket,
        Key=report_key,
        Body=report.encode("utf-8"),
        ContentType="text/plain",
    )
    print(f"Saved s3://{bucket}/{report_key}")
    return {"status": "ok", "report": report_key}
