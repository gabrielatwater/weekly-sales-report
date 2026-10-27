"""AWS Lambda entry point: builds the sales report in the cloud and emails it.

This function runs in two situations:
  - Every Monday, started by the weekly schedule (EventBridge)
  - Whenever a new .csv file is uploaded to the input/ folder of the S3 bucket

What happens each time:
  1. Download the sales CSV from S3
  2. Calculate the weekly numbers (same code as the local version)
  3. Write the report to reports/weekly_report_<date>.txt in the same bucket
  4. Email the report (if email is configured)
"""
import os
from urllib.parse import unquote_plus

import boto3

from ai_summary import ai_summary_with_fallback
from report import build_report, load_orders, split_weeks, summarize

DEFAULT_KEY = "input/sales.csv"
LOCAL_CSV = "/tmp/sales.csv"  # Lambda can only write files under /tmp

# Created once and reused if Lambda keeps the container warm
s3 = boto3.client("s3")
ssm = boto3.client("ssm")
ses = boto3.client("ses")


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


def source_key(event):
    """Decide which CSV to read.

    If S3 started us because a file was uploaded, the event says which file.
    (S3 URL-encodes the name, so "my file.csv" arrives as "my+file.csv".)
    If the weekly schedule started us, there is no file in the event, so we
    use the default one.
    """
    records = event.get("Records") or []
    if records and "s3" in records[0]:
        key = unquote_plus(records[0]["s3"]["object"]["key"])
        if key.startswith("input/"):
            return key
    return DEFAULT_KEY


def send_report_email(subject, body):
    """Email the report with Amazon SES. Returns True if it was sent."""
    sender = os.environ.get("SENDER_EMAIL")
    recipient = os.environ.get("RECIPIENT_EMAIL")
    if not sender or not recipient:
        print("Email is not configured, so no email was sent.")
        return False
    try:
        ses.send_email(
            Source=sender,
            Destination={"ToAddresses": [recipient]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
            },
        )
        print(f"Emailed the report to {recipient}")
        return True
    except Exception as error:
        # Not fatal: the report is already saved in S3
        print(f"Could not send the email: {error}")
        return False


def handler(event, context):
    """Lambda calls this function. 'event' and 'context' come from AWS."""
    bucket = os.environ["BUCKET_NAME"]
    load_groq_key()

    key = source_key(event)
    print(f"Reading s3://{bucket}/{key}")
    s3.download_file(bucket, key, LOCAL_CSV)
    orders = load_orders(LOCAL_CSV)
    if not orders:
        print("The CSV has no orders, so there is nothing to report.")
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

    emailed = send_report_email(f"Weekly sales report: {start} to {end}", report)
    return {"status": "ok", "report": report_key, "emailed": emailed}
