# Lambda function for S3 trigger
resource "aws_lambda_function" "s3_trigger" {
  filename         = data.archive_file.s3_trigger.output_path
  function_name    = "${var.project_name}-s3-trigger-${var.environment}"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "s3_trigger.lambda_handler"
  source_code_hash = data.archive_file.s3_trigger.output_base64sha256
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256
  
  environment {
    variables = {
      GITHUB_OWNER       = var.github_owner
      GITHUB_REPO        = var.github_repo
      GITHUB_TOKEN       = aws_secretsmanager_secret_version.github_token.secret_string
      DEPLOYMENTS_TABLE  = aws_dynamodb_table.deployments.name
    }
  }
  
  tags = merge(local.common_tags, {
    Name = "ServeML S3 Trigger"
  })
}

# Package Lambda function
data "archive_file" "s3_trigger" {
  type        = "zip"
  source_file = "../backend/lambda_functions/s3_trigger.py"
  output_path = "/tmp/s3_trigger.zip"
}

# Lambda permission for S3 to invoke
resource "aws_lambda_permission" "s3_trigger" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.s3_trigger.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.uploads.arn
}

# Secret for GitHub token
resource "aws_secretsmanager_secret" "github_token" {
  name = "${var.project_name}-github-token-${var.environment}"
  
  tags = merge(local.common_tags, {
    Name = "ServeML GitHub Token"
  })
}

# Secret version (value should be set manually or through CI/CD)
resource "aws_secretsmanager_secret_version" "github_token" {
  secret_id     = aws_secretsmanager_secret.github_token.id
  secret_string = "PLACEHOLDER_SET_VIA_CONSOLE_OR_CLI"
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}

# Policy for Lambda to access Secrets Manager
resource "aws_iam_role_policy" "lambda_secrets" {
  name = "${var.project_name}-lambda-secrets-${var.environment}"
  role = aws_iam_role.lambda_execution.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.github_token.arn
      }
    ]
  })
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "s3_trigger" {
  name              = "/aws/lambda/${aws_lambda_function.s3_trigger.function_name}"
  retention_in_days = 7
  
  tags = local.common_tags
}