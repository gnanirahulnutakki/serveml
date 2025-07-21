# ServeML Production Infrastructure Guidelines

This document outlines best practices and guidelines for running ServeML in production.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Infrastructure Requirements](#infrastructure-requirements)
3. [High Availability Setup](#high-availability-setup)
4. [Security Hardening](#security-hardening)
5. [Performance Optimization](#performance-optimization)
6. [Disaster Recovery](#disaster-recovery)
7. [Cost Management](#cost-management)
8. [Compliance](#compliance)

## Architecture Overview

### Production Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   CloudFront    │────▶│  Load Balancer  │────▶│   ECS Fargate   │
│  (CDN + WAF)    │     │   (ALB + TLS)   │     │  (API Backend)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                                │
         │                                                ▼
         │                                       ┌─────────────────┐
         │                                       │   DynamoDB      │
         │                                       │  (Deployments)  │
         │                                       └─────────────────┘
         │                                                │
         ▼                                                ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   S3 Bucket     │     │  Lambda@Edge    │     │     Lambda      │
│ (Static Assets) │     │  (Auth/Route)   │     │ (Model Serving) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Multi-Region Architecture

```yaml
Primary Region (us-east-1):
  - API Backend (ECS)
  - DynamoDB Global Table
  - S3 with Cross-Region Replication
  - Lambda Functions
  - CloudWatch Logs

Secondary Region (us-west-2):
  - Standby API Backend
  - DynamoDB Global Table Replica
  - S3 Replica Bucket
  - Lambda Functions (Replicated)
  - Regional CloudWatch
```

## Infrastructure Requirements

### Compute Resources

```hcl
# ECS Fargate Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "serveml-api-prod"
  network_mode            = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                     = "2048"  # 2 vCPU
  memory                  = "4096"  # 4 GB

  container_definitions = jsonencode([{
    name  = "api"
    image = "${var.ecr_repository}:latest"
    
    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]
    
    environment = [
      { name = "ENVIRONMENT", value = "production" },
      { name = "LOG_LEVEL", value = "INFO" }
    ]
    
    secrets = [
      { name = "JWT_SECRET", valueFrom = "${var.jwt_secret_arn}" },
      { name = "DATABASE_URL", valueFrom = "${var.db_url_arn}" }
    ]
    
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/aws/ecs/serveml-api"
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])
}
```

### Database Configuration

```hcl
# DynamoDB Tables
resource "aws_dynamodb_table" "deployments" {
  name           = "serveml-deployments-prod"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"
  range_key      = "deployment_id"
  
  # Enable encryption
  server_side_encryption {
    enabled = true
  }
  
  # Point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }
  
  # Global table
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  
  # TTL for old deployments
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  # Global secondary indexes
  global_secondary_index {
    name            = "status-created-index"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
  }
  
  tags = {
    Environment = "production"
    Backup      = "daily"
  }
}
```

### Network Architecture

```hcl
# VPC Configuration
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "serveml-prod-vpc"
  }
}

# Public Subnets (3 AZs)
resource "aws_subnet" "public" {
  count                   = 3
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
}

# Private Subnets (3 AZs)
resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 11}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
}

# NAT Gateways for High Availability
resource "aws_nat_gateway" "main" {
  count         = 3
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
}
```

## High Availability Setup

### 1. Multi-AZ Deployment

```yaml
ECS Service Configuration:
  Desired Count: 6 (2 per AZ)
  Deployment Strategy: Rolling Update
  Health Check Grace Period: 300s
  
Load Balancer:
  Type: Application Load Balancer
  Scheme: Internet-facing
  Availability Zones: 3
  Cross-Zone Load Balancing: Enabled
  
Target Group:
  Protocol: HTTP
  Health Check:
    Path: /health
    Interval: 30s
    Timeout: 5s
    Healthy Threshold: 2
    Unhealthy Threshold: 3
```

### 2. Auto Scaling Configuration

```hcl
# ECS Service Auto Scaling
resource "aws_appautoscaling_target" "ecs_target" {
  service_namespace  = "ecs"
  resource_id        = "service/${var.cluster_name}/${var.service_name}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = 6
  max_capacity       = 30
}

# CPU-based scaling
resource "aws_appautoscaling_policy" "cpu_scaling" {
  name               = "cpu-scaling"
  service_namespace  = "ecs"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  
  target_tracking_scaling_policy_configuration {
    target_value = 70.0
    
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Request count scaling
resource "aws_appautoscaling_policy" "request_scaling" {
  name               = "request-scaling"
  service_namespace  = "ecs"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  
  target_tracking_scaling_policy_configuration {
    target_value = 1000.0
    
    customized_metric_specification {
      metric_name = "RequestCountPerTarget"
      namespace   = "AWS/ApplicationELB"
      statistic   = "Average"
      
      dimensions {
        name  = "TargetGroup"
        value = aws_lb_target_group.api.arn_suffix
      }
    }
  }
}
```

### 3. Lambda Resilience

```python
# Lambda error handling and retry configuration
def lambda_handler(event, context):
    """Model serving handler with resilience"""
    
    # Dead letter queue for failed invocations
    dead_letter_config = {
        'TargetArn': 'arn:aws:sqs:us-east-1:123456:serveml-dlq'
    }
    
    # Retry configuration
    retry_config = {
        'MaximumRetryAttempts': 2,
        'MaximumEventAge': 3600  # 1 hour
    }
    
    # Provisioned concurrency for consistent performance
    provisioned_config = {
        'ProvisionedConcurrentExecutions': 10
    }
```

## Security Hardening

### 1. Network Security

```hcl
# Security Groups
resource "aws_security_group" "api" {
  name_prefix = "serveml-api-"
  vpc_id      = aws_vpc.main.id
  
  # Only allow traffic from ALB
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  
  # Restrict egress
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS for AWS APIs"
  }
  
  egress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [aws_subnet.database.cidr_block]
    description = "Database access"
  }
}

# WAF Rules
resource "aws_wafv2_web_acl" "api_protection" {
  name  = "serveml-api-protection"
  scope = "REGIONAL"
  
  default_action {
    allow {}
  }
  
  # Rate limiting
  rule {
    name     = "RateLimitRule"
    priority = 1
    
    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }
    
    action {
      block {}
    }
  }
  
  # SQL injection protection
  rule {
    name     = "SQLiProtection"
    priority = 2
    
    statement {
      sqli_match_statement {
        field_to_match {
          all_query_arguments {}
        }
        text_transformation {
          priority = 1
          type     = "URL_DECODE"
        }
      }
    }
    
    action {
      block {}
    }
  }
}
```

### 2. Data Encryption

```yaml
Encryption at Rest:
  - S3: AES-256 with customer-managed KMS keys
  - DynamoDB: AWS-managed encryption
  - EBS Volumes: Encrypted by default
  - Lambda Environment Variables: KMS encryption

Encryption in Transit:
  - TLS 1.2+ for all external communications
  - VPC endpoints for AWS service communication
  - Certificate pinning for mobile SDKs
```

### 3. Access Control

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## Performance Optimization

### 1. Caching Strategy

```python
# Redis configuration for caching
REDIS_CONFIG = {
    'host': 'serveml-redis.abc123.cache.amazonaws.com',
    'port': 6379,
    'db': 0,
    'decode_responses': True,
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
    'retry_on_timeout': True,
    'health_check_interval': 30
}

# Cache deployment metadata
@cache.cached(timeout=300, key_prefix='deployment')
def get_deployment(deployment_id):
    return dynamodb.get_item(Key={'deployment_id': deployment_id})
```

### 2. CDN Configuration

```hcl
resource "aws_cloudfront_distribution" "api" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "ServeML API Distribution"
  
  origin {
    domain_name = aws_lb.api.dns_name
    origin_id   = "ALB-${aws_lb.api.id}"
    
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }
  
  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "ALB-${aws_lb.api.id}"
    
    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Content-Type", "X-Requested-With"]
      
      cookies {
        forward = "none"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 31536000
  }
  
  # Cache static assets
  ordered_cache_behavior {
    path_pattern     = "/static/*"
    target_origin_id = "S3-${aws_s3_bucket.static.id}"
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 86400
    default_ttl            = 604800
    max_ttl                = 31536000
    compress               = true
  }
}
```

### 3. Database Optimization

```python
# Batch operations for DynamoDB
def batch_get_deployments(user_id, deployment_ids):
    """Efficiently fetch multiple deployments"""
    
    # Use BatchGetItem for multiple items
    response = dynamodb.batch_get_item(
        RequestItems={
            'serveml-deployments': {
                'Keys': [
                    {
                        'user_id': {'S': user_id},
                        'deployment_id': {'S': dep_id}
                    } for dep_id in deployment_ids
                ],
                'ProjectionExpression': 'deployment_id, #s, created_at',
                'ExpressionAttributeNames': {'#s': 'status'}
            }
        }
    )
    
    return response['Responses']['serveml-deployments']
```

## Disaster Recovery

### 1. Backup Strategy

```bash
#!/bin/bash
# Automated backup script

# DynamoDB backup
aws dynamodb create-backup \
  --table-name serveml-deployments-prod \
  --backup-name "serveml-backup-$(date +%Y%m%d-%H%M%S)"

# S3 cross-region replication is automatic

# Export CloudWatch Logs
aws logs create-export-task \
  --log-group-name /aws/ecs/serveml-api \
  --from $(date -d '1 day ago' +%s)000 \
  --to $(date +%s)000 \
  --destination serveml-logs-backup \
  --destination-prefix "logs/$(date +%Y/%m/%d)"
```

### 2. Recovery Procedures

```yaml
RTO (Recovery Time Objective): 15 minutes
RPO (Recovery Point Objective): 5 minutes

Recovery Steps:
  1. Database Recovery:
     - DynamoDB: Restore from point-in-time recovery
     - Time: ~5 minutes
  
  2. Compute Recovery:
     - ECS: Update service to increase desired count
     - Lambda: No action needed (serverless)
     - Time: ~3 minutes
  
  3. Network Recovery:
     - Route 53: Update weighted routing
     - CloudFront: No action needed
     - Time: ~2 minutes
  
  4. Verification:
     - Run health checks
     - Test critical user flows
     - Monitor error rates
     - Time: ~5 minutes
```

### 3. Failover Configuration

```hcl
# Route 53 Health Checks
resource "aws_route53_health_check" "primary" {
  fqdn              = "api.serveml.com"
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health"
  failure_threshold = 3
  request_interval  = 30
}

# Weighted routing for gradual failover
resource "aws_route53_record" "api_primary" {
  zone_id = var.zone_id
  name    = "api.serveml.com"
  type    = "A"
  
  weighted_routing_policy {
    weight = var.primary_weight  # Start at 100, reduce during issues
  }
  
  alias {
    name                   = aws_cloudfront_distribution.api.domain_name
    zone_id                = aws_cloudfront_distribution.api.hosted_zone_id
    evaluate_target_health = true
  }
}
```

## Cost Management

### 1. Cost Allocation Tags

```hcl
locals {
  common_tags = {
    Environment  = "production"
    Project      = "serveml"
    CostCenter   = "engineering"
    Owner        = "platform-team"
    AutoShutdown = "false"
  }
}
```

### 2. Resource Optimization

```yaml
Cost Optimization Strategies:
  
  Compute:
    - Use Fargate Spot for non-critical tasks (70% discount)
    - Right-size container resources based on metrics
    - Implement request-based auto-scaling
  
  Storage:
    - S3 Intelligent-Tiering for model storage
    - Lifecycle policies for old deployments
    - Compress large models before storage
  
  Data Transfer:
    - Use CloudFront for edge caching
    - VPC endpoints to avoid NAT charges
    - Compress API responses
  
  Database:
    - DynamoDB on-demand for variable workloads
    - Auto-scaling for predictable patterns
    - Archive old deployment data
```

### 3. Budget Alerts

```json
{
  "BudgetName": "ServeML-Production",
  "BudgetLimit": {
    "Amount": "10000",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "CostFilters": {
    "TagKeyValue": ["Project$serveml", "Environment$production"]
  },
  "CostTypes": {
    "IncludeTax": true,
    "IncludeSubscription": true,
    "UseBlended": false
  },
  "NotificationsWithSubscribers": [
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [
        {
          "Address": "platform-team@serveml.com",
          "SubscriptionType": "EMAIL"
        }
      ]
    }
  ]
}
```

## Compliance

### 1. Data Residency

```yaml
Regional Deployment:
  US: us-east-1 (primary), us-west-2 (DR)
  EU: eu-west-1 (primary), eu-central-1 (DR)
  APAC: ap-southeast-1 (primary), ap-northeast-1 (DR)

Data Isolation:
  - Separate AWS accounts per region
  - No cross-region data replication (except DR)
  - Regional DynamoDB tables
```

### 2. Audit Logging

```hcl
# CloudTrail Configuration
resource "aws_cloudtrail" "audit" {
  name                          = "serveml-audit-trail"
  s3_bucket_name               = aws_s3_bucket.audit_logs.id
  include_global_service_events = true
  is_multi_region_trail        = true
  enable_log_file_validation   = true
  
  event_selector {
    read_write_type           = "All"
    include_management_events = true
    
    data_resource {
      type   = "AWS::S3::Object"
      values = ["${aws_s3_bucket.models.arn}/*"]
    }
    
    data_resource {
      type   = "AWS::DynamoDB::Table"
      values = [aws_dynamodb_table.deployments.arn]
    }
  }
}
```

### 3. Compliance Standards

```yaml
SOC 2 Type II:
  - Annual audits
  - Continuous monitoring
  - Incident response procedures
  
GDPR:
  - Data processing agreements
  - Right to deletion implementation
  - Data portability APIs
  
HIPAA (if applicable):
  - BAA with AWS
  - Encryption requirements
  - Access controls
```

## Monitoring Checklist

### Pre-Production
- [ ] All infrastructure provisioned
- [ ] Security groups configured
- [ ] SSL certificates valid
- [ ] Monitoring dashboards created
- [ ] Alerts configured
- [ ] Backup procedures tested

### Go-Live
- [ ] DNS records updated
- [ ] Load balancer health checks passing
- [ ] Auto-scaling policies active
- [ ] CloudWatch alarms armed
- [ ] On-call rotation scheduled

### Post-Production
- [ ] Performance baselines established
- [ ] Cost tracking enabled
- [ ] Security scans scheduled
- [ ] Disaster recovery drills planned
- [ ] Compliance audits scheduled