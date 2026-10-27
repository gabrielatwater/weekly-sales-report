output "bucket_name" {
  description = "The S3 bucket holding the input data and the reports"
  value       = aws_s3_bucket.reports.id
}

output "lambda_function_name" {
  description = "The Lambda function that builds the report"
  value       = aws_lambda_function.report.function_name
}

output "run_it_now" {
  description = "Command to run the report immediately instead of waiting for Monday"
  value       = "aws lambda invoke --function-name ${aws_lambda_function.report.function_name} --cli-binary-format raw-in-base64-out /tmp/out.json && cat /tmp/out.json"
}

output "list_reports" {
  description = "Command to list the finished reports"
  value       = "aws s3 ls s3://${aws_s3_bucket.reports.id}/reports/"
}
