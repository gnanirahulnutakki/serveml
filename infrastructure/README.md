# ServeML Infrastructure

This directory contains Terraform configurations for deploying ServeML infrastructure on AWS.

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.0
3. **GitHub Personal Access Token** for triggering workflows

## Quick Start

1. **Initialize Terraform**:
   ```bash
   terraform init
   ```

2. **Copy and update variables**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

3. **Plan the deployment**:
   ```bash
   terraform plan
   ```

4. **Apply the configuration**:
   ```bash
   terraform apply
   ```

5. **Set GitHub token** (after infrastructure is created):
   ```bash
   aws secretsmanager update-secret \
     --secret-id serveml-github-token-dev \
     --secret-string "your-github-token"
   ```

## Infrastructure Components

### Storage
- **S3 Buckets**:
  - Uploads bucket for model files
  - Lambda deployments bucket
  - Versioning and encryption enabled
  - Lifecycle policies for cost optimization

### Database
- **DynamoDB Tables**:
  - Deployments table (user_id, deployment_id)
  - Users table (user_id, email index)
  - Metrics table (deployment_id, timestamp)
  - Pay-per-request billing mode

### Container Registry
- **ECR Repositories**:
  - Models repository for deployment containers
  - Base images repository
  - Vulnerability scanning enabled

### Compute
- **Lambda Functions**:
  - S3 trigger function for deployment automation
  - Configured with appropriate IAM roles

### Security
- **IAM Roles**:
  - Lambda execution role
  - Model Lambda role
  - GitHub Actions role (OIDC)
  - Least-privilege policies

## Cost Estimation

Monthly costs for a typical deployment:
- S3: ~$5 (assuming 10GB storage)
- DynamoDB: ~$5 (pay-per-request)
- ECR: ~$10 (assuming 50GB storage)
- Lambda: Variable based on usage
- Total: ~$20-50/month for development

## GitHub Actions Setup

1. **Configure OIDC Provider** (one-time setup):
   ```bash
   aws iam create-open-id-connect-provider \
     --url https://token.actions.githubusercontent.com \
     --client-id-list sts.amazonaws.com
   ```

2. **Update GitHub Secrets**:
   - `AWS_ACCOUNT_ID`: Your AWS account ID
   - `AWS_DEPLOY_ROLE_ARN`: Output from Terraform
   - `LAMBDA_ROLE_ARN`: Output from Terraform
   - `S3_BUCKET`: Output from Terraform

## Monitoring

- CloudWatch Logs: `/aws/lambda/serveml-*`
- DynamoDB metrics: Available in AWS Console
- S3 metrics: Available in AWS Console

## Cleanup

To destroy all resources:
```bash
terraform destroy
```

**Warning**: This will delete all data. Ensure you have backups if needed.

## Troubleshooting

### S3 Bucket Already Exists
S3 bucket names must be globally unique. Update `s3_bucket_prefix` in your tfvars file.

### Lambda Function Not Triggering
1. Check CloudWatch Logs for errors
2. Verify S3 event notifications are configured
3. Ensure GitHub token is set correctly

### Permission Denied Errors
1. Verify AWS credentials have sufficient permissions
2. Check IAM role trust relationships
3. Ensure service-linked roles exist

## Production Considerations

1. **Enable deletion protection**:
   ```hcl
   enable_deletion_protection = true
   ```

2. **Use separate AWS accounts** for dev/staging/prod

3. **Enable AWS Config** for compliance monitoring

4. **Set up AWS Budget alerts** for cost control

5. **Configure backup policies** for DynamoDB tables

6. **Use AWS KMS** for encryption keys instead of default

7. **Set up VPC endpoints** for private communication