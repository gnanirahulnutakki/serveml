# DynamoDB table for deployments
resource "aws_dynamodb_table" "deployments" {
  name           = "${var.dynamodb_table_prefix}-deployments-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"
  range_key      = "deployment_id"
  
  attribute {
    name = "user_id"
    type = "S"
  }
  
  attribute {
    name = "deployment_id"
    type = "S"
  }
  
  attribute {
    name = "status"
    type = "S"
  }
  
  attribute {
    name = "created_at"
    type = "S"
  }
  
  # Global secondary index for querying by status
  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
  }
  
  # Enable point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }
  
  # Enable encryption
  server_side_encryption {
    enabled = true
  }
  
  tags = merge(local.common_tags, {
    Name = "ServeML Deployments Table"
  })
}

# DynamoDB table for users
resource "aws_dynamodb_table" "users" {
  name           = "${var.dynamodb_table_prefix}-users-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"
  
  attribute {
    name = "user_id"
    type = "S"
  }
  
  attribute {
    name = "email"
    type = "S"
  }
  
  # Global secondary index for email lookup
  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }
  
  # Enable point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }
  
  # Enable encryption
  server_side_encryption {
    enabled = true
  }
  
  tags = merge(local.common_tags, {
    Name = "ServeML Users Table"
  })
}

# DynamoDB table for metrics
resource "aws_dynamodb_table" "metrics" {
  name           = "${var.dynamodb_table_prefix}-metrics-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "deployment_id"
  range_key      = "timestamp"
  
  attribute {
    name = "deployment_id"
    type = "S"
  }
  
  attribute {
    name = "timestamp"
    type = "N"
  }
  
  # TTL for automatic cleanup
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  # Enable encryption
  server_side_encryption {
    enabled = true
  }
  
  tags = merge(local.common_tags, {
    Name = "ServeML Metrics Table"
  })
}