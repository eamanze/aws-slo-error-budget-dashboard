variable "aws_region" {
  description = "AWS region for the workload."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Lowercase name used in resource names."
  type        = string
  default     = "sre-slo-demo"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.project_name))
    error_message = "project_name must be 3-31 lowercase alphanumeric or hyphen characters."
  }
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "dev"
}

variable "container_image" {
  description = "Immutable container image reference, preferably an ECR digest."
  type        = string
}

variable "certificate_arn" {
  description = "Optional ACM certificate ARN. When set, HTTP redirects to HTTPS."
  type        = string
  default     = null
}

variable "desired_count" {
  description = "Normal ECS task count. Use at least two to demonstrate AZ resilience."
  type        = number
  default     = 2

  validation {
    condition     = var.desired_count >= 2
    error_message = "desired_count must be at least two."
  }
}

variable "monthly_budget_usd" {
  description = "Monthly AWS cost threshold for notification."
  type        = number
  default     = 75
}

variable "budget_email" {
  description = "Optional email address for AWS Budget notifications."
  type        = string
  default     = null
  sensitive   = true
}

