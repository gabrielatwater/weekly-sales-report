data "aws_caller_identity" "current" {}

locals {
  # S3 bucket names must be unique across ALL of AWS, so we add your account ID
  bucket_name   = "${var.project_name}-${data.aws_caller_identity.current.account_id}"
  function_name = "${var.project_name}-lambda"

  # Where the Groq key is stored. We create it by hand (see README), NOT with
  # Terraform, so the secret never ends up in Terraform's state file.
  groq_parameter_name = "/${var.project_name}/groq-api-key"
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
# Zip up the folder made by build.sh: our Python files plus the groq library.
# Run "bash build.sh" before terraform plan/apply, or this folder won't exist.
data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/build/package"
  output_path = "${path.module}/build/lambda.zip"
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

# Least privilege again: the function may read ONE parameter, nothing else in
# Parameter Store. Note the ARN has "parameter" followed directly by the name,
# which already starts with a slash.
data "aws_iam_policy_document" "groq_key_access" {
  statement {
    actions   = ["ssm:GetParameter"]
    resources = ["arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${local.groq_parameter_name}"]
  }
}

resource "aws_iam_role_policy" "groq_key_access" {
  name   = "groq-key-access"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.groq_key_access.json
}

# ------------------------------------------------------------------ Email (SES)
# Amazon SES only sends from addresses you have proven you own. Creating these
# makes AWS email each address a verification link that you must click once.
# toset() removes duplicates, so using the same address for both is fine.
resource "aws_ses_email_identity" "verified" {
  for_each = toset([var.sender_email, var.recipient_email])
  email    = each.value
}

# The function may send email only involving our two verified addresses. (In
# SES "sandbox" mode, AWS also checks permission on the recipient's address.)
data "aws_iam_policy_document" "send_email" {
  statement {
    actions   = ["ses:SendEmail"]
    resources = [for identity in aws_ses_email_identity.verified : identity.arn]
  }
}

resource "aws_iam_role_policy" "send_email" {
  name   = "send-email"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.send_email.json
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
  architectures    = ["x86_64"] # must match the platform build.sh packages for
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 60  # the AI call needs more time than the rule-based version
  memory_size      = 256 # the groq library needs more memory than plain Python

  environment {
    variables = {
      BUCKET_NAME         = aws_s3_bucket.reports.id
      GROQ_PARAMETER_NAME = local.groq_parameter_name
      SENDER_EMAIL        = var.sender_email
      RECIPIENT_EMAIL     = var.recipient_email
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

# ------------------------------------------------- Run when a new CSV is uploaded
# Gives S3 permission to start the function, but only for events from OUR bucket
resource "aws_lambda_permission" "allow_s3" {
  statement_id   = "AllowS3Invoke"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.report.function_name
  principal      = "s3.amazonaws.com"
  source_arn     = aws_s3_bucket.reports.arn
  source_account = data.aws_caller_identity.current.account_id
}

# Start the function when a .csv file lands in input/. Reports are written to
# reports/, a different folder, so the function can never trigger itself.
resource "aws_s3_bucket_notification" "new_data" {
  bucket = aws_s3_bucket.reports.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.report.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "input/"
    filter_suffix       = ".csv"
  }

  # Create this after the sample data upload, so deploying doesn't send an email
  depends_on = [
    aws_lambda_permission.allow_s3,
    aws_s3_object.sample_data,
  ]
}
