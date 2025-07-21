output "uploads_bucket_name" {
  description = "Name of the S3 bucket for uploads"
  value       = aws_s3_bucket.uploads.id
}

output "uploads_bucket_arn" {
  description = "ARN of the S3 bucket for uploads"
  value       = aws_s3_bucket.uploads.arn
}

output "ecr_repository_url" {
  description = "URL of the ECR repository for model containers"
  value       = aws_ecr_repository.models.repository_url
}

output "deployments_table_name" {
  description = "Name of the DynamoDB deployments table"
  value       = aws_dynamodb_table.deployments.name
}

output "users_table_name" {
  description = "Name of the DynamoDB users table"
  value       = aws_dynamodb_table.users.name
}

output "metrics_table_name" {
  description = "Name of the DynamoDB metrics table"
  value       = aws_dynamodb_table.metrics.name
}

output "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}

output "model_lambda_role_arn" {
  description = "ARN of the model Lambda execution role"
  value       = aws_iam_role.model_lambda.arn
}

output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions role"
  value       = aws_iam_role.github_actions.arn
}

output "s3_trigger_function_name" {
  description = "Name of the S3 trigger Lambda function"
  value       = aws_lambda_function.s3_trigger.function_name
}

output "region" {
  description = "AWS region"
  value       = var.aws_region
}

output "account_id" {
  description = "AWS account ID"
  value       = local.account_id
}