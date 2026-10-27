variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name used to label and name the resources"
  type        = string
  default     = "weekly-sales-report"
}

variable "schedule" {
  description = "When the report runs, as an EventBridge cron expression (UTC)"
  type        = string
  default     = "cron(0 13 ? * MON *)" # Mondays at 13:00 UTC (8:00 AM in Colombia and New York)
}
