# S3 Bucket for model uploads
resource "aws_s3_bucket" "uploads" {
  bucket = "${var.s3_bucket_prefix}-uploads-${var.environment}-${local.account_id}"
  
  tags = merge(local.common_tags, {
    Name = "ServeML Uploads Bucket"
  })
}

# Enable versioning
resource "aws_s3_bucket_versioning" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle rules for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  
  rule {
    id     = "delete-old-uploads"
    status = "Enabled"
    
    expiration {
      days = 90
    }
    
    filter {
      prefix = "deployments/"
    }
  }
  
  rule {
    id     = "transition-to-ia"
    status = "Enabled"
    
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    filter {
      prefix = "deployments/"
    }
  }
}

# S3 Event Notification to Lambda
resource "aws_s3_bucket_notification" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  
  lambda_function {
    lambda_function_arn = aws_lambda_function.s3_trigger.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "deployments/"
    filter_suffix       = "trigger.json"
  }
  
  depends_on = [aws_lambda_permission.s3_trigger]
}

# S3 bucket for Lambda deployment packages
resource "aws_s3_bucket" "lambda_deployments" {
  bucket = "${var.s3_bucket_prefix}-lambda-deployments-${var.environment}-${local.account_id}"
  
  tags = merge(local.common_tags, {
    Name = "ServeML Lambda Deployments"
  })
}

# Enable versioning for Lambda deployments
resource "aws_s3_bucket_versioning" "lambda_deployments" {
  bucket = aws_s3_bucket.lambda_deployments.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# CORS configuration for uploads bucket
resource "aws_s3_bucket_cors_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = ["http://localhost:3000", "https://serveml.com"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}