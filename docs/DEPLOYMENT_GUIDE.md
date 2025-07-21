# ServeML Deployment Guide

This guide covers deploying ServeML to production on AWS.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Application Deployment](#application-deployment)
4. [Configuration](#configuration)
5. [Security](#security)
6. [Scaling](#scaling)
7. [Maintenance](#maintenance)

## Prerequisites

### Required Tools

- AWS CLI v2.x
- Terraform v1.5+
- Docker 24.x+
- Python 3.9+
- Node.js 18+
- GitHub CLI

### AWS Account Setup

1. **Create AWS Account**
   ```bash
   # Configure AWS CLI
   aws configure
   ```

2. **Create IAM User for Deployment**
   ```bash
   aws iam create-user --user-name serveml-deploy
   aws iam attach-user-policy --user-name serveml-deploy \
     --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
   ```

3. **Set up AWS Systems Manager Parameters**
   ```bash
   # Store secrets
   aws ssm put-parameter --name /serveml/prod/jwt-secret \
     --value "$(openssl rand -hex 32)" --type SecureString
   
   aws ssm put-parameter --name /serveml/prod/db-password \
     --value "$(openssl rand -hex 16)" --type SecureString
   ```

## Infrastructure Setup

### 1. Initialize Terraform

```bash
cd infrastructure
terraform init
terraform workspace new prod
```

### 2. Configure Variables

Create `terraform.tfvars`:

```hcl
environment = "prod"
aws_region = "us-east-1"
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

# Networking
vpc_cidr = "10.0.0.0/16"
public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]

# Compute
lambda_memory_size = 3008
lambda_timeout = 300
lambda_reserved_concurrent_executions = 100

# Storage
dynamodb_read_capacity = 5
dynamodb_write_capacity = 5

# Domain
domain_name = "serveml.com"
certificate_arn = "arn:aws:acm:us-east-1:xxxx:certificate/yyyy"
```

### 3. Deploy Infrastructure

```bash
# Plan deployment
terraform plan -out=tfplan

# Apply infrastructure
terraform apply tfplan

# Save outputs
terraform output -json > infrastructure_outputs.json
```

## Application Deployment

### 1. Backend Deployment

#### Build and Push Docker Image

```bash
cd backend

# Build Docker image
docker build -t serveml-backend:latest .

# Tag for ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $ECR_REGISTRY

docker tag serveml-backend:latest \
  $ECR_REGISTRY/serveml-backend:latest

# Push to ECR
docker push $ECR_REGISTRY/serveml-backend:latest
```

#### Deploy to ECS Fargate

```bash
# Update task definition
aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition.json

# Update service
aws ecs update-service \
  --cluster serveml-prod \
  --service serveml-backend \
  --task-definition serveml-backend:latest \
  --force-new-deployment
```

### 2. Frontend Deployment

```bash
cd frontend

# Build production bundle
npm install
npm run build

# Deploy to S3
aws s3 sync dist/ s3://serveml-frontend-prod/ \
  --delete \
  --cache-control "public, max-age=3600"

# Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_ID \
  --paths "/*"
```

### 3. Lambda Functions Deployment

```bash
# Deploy model serving wrapper
cd backend/templates

# Create deployment package
zip -r wrapper.zip wrapper.py requirements.txt

# Update Lambda function
aws lambda update-function-code \
  --function-name serveml-model-wrapper \
  --zip-file fileb://wrapper.zip
```

## Configuration

### Environment Variables

#### Backend (ECS)

```json
{
  "environment": [
    {"name": "AWS_REGION", "value": "us-east-1"},
    {"name": "DYNAMODB_TABLE", "value": "serveml-deployments-prod"},
    {"name": "S3_BUCKET", "value": "serveml-models-prod"},
    {"name": "ECR_REGISTRY", "value": "xxxx.dkr.ecr.us-east-1.amazonaws.com"},
    {"name": "CORS_ORIGINS", "value": "https://serveml.com"},
    {"name": "LOG_LEVEL", "value": "INFO"}
  ]
}
```

#### Frontend

Create `.env.production`:

```env
VITE_API_URL=https://api.serveml.com
VITE_AWS_REGION=us-east-1
VITE_USER_POOL_ID=us-east-1_xxxxxxxxx
VITE_USER_POOL_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Database Configuration

```bash
# Create DynamoDB tables
aws dynamodb create-table \
  --table-name serveml-deployments-prod \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=deployment_id,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
    AttributeName=deployment_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES
```

## Security

### 1. SSL/TLS Configuration

```bash
# Request ACM certificate
aws acm request-certificate \
  --domain-name serveml.com \
  --subject-alternative-names "*.serveml.com" \
  --validation-method DNS
```

### 2. WAF Configuration

```bash
# Create WAF web ACL
aws wafv2 create-web-acl \
  --name serveml-prod-acl \
  --scope CLOUDFRONT \
  --default-action Allow={} \
  --rules file://waf-rules.json
```

### 3. Security Groups

```bash
# Backend security group
aws ec2 create-security-group \
  --group-name serveml-backend-sg \
  --description "Security group for ServeML backend" \
  --vpc-id $VPC_ID

# Allow HTTPS only
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 443 \
  --source-group $ALB_SG_ID
```

### 4. Secrets Management

```bash
# Rotate secrets regularly
aws secretsmanager create-secret \
  --name serveml/prod/api-keys \
  --secret-string file://api-keys.json

# Enable automatic rotation
aws secretsmanager put-secret-rotation \
  --secret-id serveml/prod/api-keys \
  --rotation-lambda-arn $ROTATION_LAMBDA_ARN \
  --rotation-rules AutomaticallyAfterDays=30
```

## Scaling

### 1. Auto Scaling Configuration

#### ECS Service Auto Scaling

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/serveml-prod/serveml-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

# Create scaling policy
aws application-autoscaling put-scaling-policy \
  --policy-name cpu-scaling \
  --service-namespace ecs \
  --resource-id service/serveml-prod/serveml-backend \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://cpu-scaling-policy.json
```

#### Lambda Concurrency

```bash
# Set reserved concurrent executions
aws lambda put-function-concurrency \
  --function-name serveml-model-serving \
  --reserved-concurrent-executions 100

# Configure provisioned concurrency
aws lambda put-provisioned-concurrency-config \
  --function-name serveml-model-serving \
  --qualifier prod \
  --provisioned-concurrent-executions 10
```

### 2. DynamoDB Auto Scaling

```bash
# Enable auto scaling
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/serveml-deployments-prod \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 \
  --max-capacity 100
```

## Maintenance

### 1. Backup Strategy

#### Database Backups

```bash
# Enable point-in-time recovery
aws dynamodb update-continuous-backups \
  --table-name serveml-deployments-prod \
  --point-in-time-recovery-specification \
    PointInTimeRecoveryEnabled=true

# Create on-demand backup
aws dynamodb create-backup \
  --table-name serveml-deployments-prod \
  --backup-name serveml-backup-$(date +%Y%m%d)
```

#### S3 Backups

```bash
# Enable versioning
aws s3api put-bucket-versioning \
  --bucket serveml-models-prod \
  --versioning-configuration Status=Enabled

# Configure lifecycle rules
aws s3api put-bucket-lifecycle-configuration \
  --bucket serveml-models-prod \
  --lifecycle-configuration file://s3-lifecycle.json
```

### 2. Monitoring Setup

```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name ServeML-Prod \
  --dashboard-body file://cloudwatch-dashboard.json

# Set up alarms
aws cloudwatch put-metric-alarm \
  --alarm-name serveml-high-error-rate \
  --alarm-description "High error rate in ServeML API" \
  --metric-name 4XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### 3. Log Aggregation

```bash
# Create log groups
aws logs create-log-group --log-group-name /aws/ecs/serveml-backend
aws logs create-log-group --log-group-name /aws/lambda/serveml-model-serving

# Set retention
aws logs put-retention-policy \
  --log-group-name /aws/ecs/serveml-backend \
  --retention-in-days 30
```

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing
- [ ] Security scan completed
- [ ] Dependencies updated
- [ ] Documentation updated
- [ ] Database migrations prepared
- [ ] Rollback plan ready

### Deployment Steps

1. [ ] Deploy infrastructure changes
2. [ ] Update backend services
3. [ ] Deploy Lambda functions
4. [ ] Update frontend
5. [ ] Run smoke tests
6. [ ] Monitor metrics
7. [ ] Update DNS if needed

### Post-Deployment

- [ ] Verify all services healthy
- [ ] Check CloudWatch metrics
- [ ] Test critical user flows
- [ ] Monitor error rates
- [ ] Update status page
- [ ] Notify stakeholders

## Rollback Procedure

### Quick Rollback

```bash
# ECS service rollback
aws ecs update-service \
  --cluster serveml-prod \
  --service serveml-backend \
  --task-definition serveml-backend:previous \
  --force-new-deployment

# Lambda rollback
aws lambda update-function-code \
  --function-name serveml-model-serving \
  --s3-bucket serveml-deployments \
  --s3-key lambda/previous-version.zip

# Frontend rollback
aws s3 sync s3://serveml-frontend-backup/ s3://serveml-frontend-prod/ \
  --delete
```

## Troubleshooting

### Common Issues

1. **Lambda Cold Starts**
   - Enable provisioned concurrency
   - Optimize package size
   - Use Lambda SnapStart

2. **DynamoDB Throttling**
   - Enable auto-scaling
   - Use on-demand billing
   - Implement exponential backoff

3. **S3 Access Denied**
   - Check bucket policies
   - Verify IAM roles
   - Check CORS configuration

### Debug Commands

```bash
# Check ECS service
aws ecs describe-services \
  --cluster serveml-prod \
  --services serveml-backend

# View Lambda logs
aws logs tail /aws/lambda/serveml-model-serving --follow

# Check DynamoDB metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name UserErrors \
  --dimensions Name=TableName,Value=serveml-deployments-prod \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

## Support

For deployment issues:
- Check CloudWatch logs
- Review AWS Personal Health Dashboard
- Contact: devops@serveml.com
- Slack: #serveml-ops