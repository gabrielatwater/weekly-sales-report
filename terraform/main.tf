data "aws_caller_identity" "current" {}

locals {
  # S3 bucket names must be unique across ALL of AWS, so we add your account ID
  bucket_name   = "${var.project_name}-${data.aws_caller_identity.current.account_id}"
  function_name = "${var.project_name}-lambda"
}

# ---------------------------------------------------------------- S3 bucket
resource "aws_s3_bucket" "reports" {
  bucket        = local.bucket_name
  force_destroy = true # lets "terraform destroy" delete the bucket even if it has files
}

resource "aws_s3_bucket_public_access_block" "reports" {
  bucket                  = aws_s3_bucket.reports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Upload the sample data so there is something to report on
resource "aws_s3_object" "sample_data" {
  bucket = aws_s3_bucket.reports.id
  key    = "input/sales.csv"
  source = "${path.module}/../sales.csv"
  etag   = filemd5("${path.module}/../sales.csv")
}

# ------------------------------------------------------------ Lambda package
# Zip up the Python files the function needs
data "archive_file" "lambda" {
  type        = "zip"
  output_path = "${path.module}/build/lambda.zip"

  source {
    content  = file("${path.module}/../lambda_function.py")
    filename = "lambda_function.py"
  }
  source {
    content  = file("${path.module}/../report.py")
    filename = "report.py"
  }
  source {
    content  = file("${path.module}/../summary.py")
    filename = "summary.py"
  }
  source {
    content  = file("${path.module}/../ai_summary.py")
    filename = "ai_summary.py"
  }
}

# --------------------------------------------------------------- IAM (permissions)
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

# Lets the function write its logs
resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Least privilege: read the input file, write only into reports/
data "aws_iam_policy_document" "bucket_access" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.reports.arn}/input/*"]
  }
  statement {
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.reports.arn}/reports/*"]
  }
}

resource "aws_iam_role_policy" "bucket_access" {
  name   = "bucket-access"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.bucket_access.json
}

# ------------------------------------------------------------------- Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 14 # old logs get deleted automatically
}

resource "aws_lambda_function" "report" {
  function_name    = local.function_name
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "lambda_function.handler"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 30
  memory_size      = 128

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.reports.id
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy_attachment.logs,
  ]
}

# --------------------------------------------------------------- Weekly schedule
resource "aws_cloudwatch_event_rule" "weekly" {
  name                = "${var.project_name}-weekly"
  description         = "Runs the weekly sales report"
  schedule_expression = var.schedule
}

resource "aws_cloudwatch_event_target" "weekly" {
  rule = aws_cloudwatch_event_rule.weekly.name
  arn  = aws_lambda_function.report.arn
}

# Gives the schedule permission to start the function
resource "aws_lambda_permission" "allow_schedule" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.report.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly.arn
}
