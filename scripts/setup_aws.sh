#!/bin/bash

# ServeML AWS Setup Script
# This script helps set up AWS resources for ServeML deployment

set -e

echo "================================================"
echo "     ServeML AWS Setup Script"
echo "================================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}
PROJECT_NAME="serveml"
ENVIRONMENT="prod"

# Check prerequisites
check_prerequisites() {
    echo -e "\n${YELLOW}Checking prerequisites...${NC}"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}❌ AWS CLI not found. Please install: https://aws.amazon.com/cli/${NC}"
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        echo -e "${RED}❌ Terraform not found. Please install: https://www.terraform.io/downloads${NC}"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}❌ AWS credentials not configured. Run: aws configure${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ All prerequisites met${NC}"
}

# Create S3 bucket for Terraform state
create_terraform_backend() {
    echo -e "\n${YELLOW}Creating Terraform backend...${NC}"
    
    BUCKET_NAME="${PROJECT_NAME}-terraform-state-${AWS_REGION}"
    
    # Create bucket
    if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
        echo "Bucket already exists: $BUCKET_NAME"
    else
        aws s3api create-bucket \
            --bucket "$BUCKET_NAME" \
            --region "$AWS_REGION" \
            $([ "$AWS_REGION" != "us-east-1" ] && echo "--create-bucket-configuration LocationConstraint=$AWS_REGION")
        
        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "$BUCKET_NAME" \
            --versioning-configuration Status=Enabled
        
        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket "$BUCKET_NAME" \
            --server-side-encryption-configuration '{
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }'
        
        echo -e "${GREEN}✓ Created S3 bucket: $BUCKET_NAME${NC}"
    fi
    
    # Create DynamoDB table for state locking
    TABLE_NAME="${PROJECT_NAME}-terraform-locks"
    
    if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$AWS_REGION" &> /dev/null; then
        echo "DynamoDB table already exists: $TABLE_NAME"
    else
        aws dynamodb create-table \
            --table-name "$TABLE_NAME" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "$AWS_REGION"
        
        echo -e "${GREEN}✓ Created DynamoDB table: $TABLE_NAME${NC}"
    fi
}

# Create ECR repositories
create_ecr_repositories() {
    echo -e "\n${YELLOW}Creating ECR repositories...${NC}"
    
    REPOS=("${PROJECT_NAME}-backend" "${PROJECT_NAME}-models")
    
    for repo in "${REPOS[@]}"; do
        if aws ecr describe-repositories --repository-names "$repo" --region "$AWS_REGION" &> /dev/null; then
            echo "ECR repository already exists: $repo"
        else
            aws ecr create-repository \
                --repository-name "$repo" \
                --region "$AWS_REGION" \
                --image-scanning-configuration scanOnPush=true \
                --encryption-configuration encryptionType=AES256
            
            # Set lifecycle policy
            aws ecr put-lifecycle-policy \
                --repository-name "$repo" \
                --lifecycle-policy-text '{
                    "rules": [{
                        "rulePriority": 1,
                        "description": "Keep last 10 images",
                        "selection": {
                            "tagStatus": "any",
                            "countType": "imageCountMoreThan",
                            "countNumber": 10
                        },
                        "action": {
                            "type": "expire"
                        }
                    }]
                }' \
                --region "$AWS_REGION"
            
            echo -e "${GREEN}✓ Created ECR repository: $repo${NC}"
        fi
    done
}

# Create KMS keys
create_kms_keys() {
    echo -e "\n${YELLOW}Creating KMS keys...${NC}"
    
    # Create key for secrets
    KEY_ALIAS="alias/${PROJECT_NAME}-secrets"
    
    if aws kms describe-key --key-id "$KEY_ALIAS" --region "$AWS_REGION" &> /dev/null; then
        echo "KMS key already exists: $KEY_ALIAS"
    else
        # Create key
        KEY_ID=$(aws kms create-key \
            --description "ServeML secrets encryption key" \
            --key-usage ENCRYPT_DECRYPT \
            --origin AWS_KMS \
            --region "$AWS_REGION" \
            --query 'KeyMetadata.KeyId' \
            --output text)
        
        # Create alias
        aws kms create-alias \
            --alias-name "$KEY_ALIAS" \
            --target-key-id "$KEY_ID" \
            --region "$AWS_REGION"
        
        echo -e "${GREEN}✓ Created KMS key: $KEY_ALIAS${NC}"
    fi
}

# Create initial secrets
create_secrets() {
    echo -e "\n${YELLOW}Creating initial secrets...${NC}"
    
    # Generate JWT secret
    JWT_SECRET=$(openssl rand -hex 32)
    
    # Store in Parameter Store
    aws ssm put-parameter \
        --name "/${PROJECT_NAME}/${ENVIRONMENT}/jwt-secret" \
        --value "$JWT_SECRET" \
        --type SecureString \
        --key-id "$KEY_ALIAS" \
        --region "$AWS_REGION" \
        --overwrite || true
    
    echo -e "${GREEN}✓ Created JWT secret${NC}"
    
    # Create other necessary secrets
    SECRETS=(
        "db-password:$(openssl rand -hex 16)"
        "api-key:$(openssl rand -hex 32)"
    )
    
    for secret in "${SECRETS[@]}"; do
        name="${secret%%:*}"
        value="${secret#*:}"
        
        aws ssm put-parameter \
            --name "/${PROJECT_NAME}/${ENVIRONMENT}/${name}" \
            --value "$value" \
            --type SecureString \
            --key-id "$KEY_ALIAS" \
            --region "$AWS_REGION" \
            --overwrite || true
    done
    
    echo -e "${GREEN}✓ Created all secrets${NC}"
}

# Create Route53 hosted zone (optional)
create_hosted_zone() {
    echo -e "\n${YELLOW}Route53 Hosted Zone Setup${NC}"
    read -p "Do you have a domain name to use? (y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your domain name (e.g., serveml.com): " DOMAIN_NAME
        
        # Check if zone exists
        ZONE_ID=$(aws route53 list-hosted-zones-by-name \
            --query "HostedZones[?Name=='${DOMAIN_NAME}.'].Id" \
            --output text)
        
        if [ -z "$ZONE_ID" ]; then
            # Create hosted zone
            ZONE_ID=$(aws route53 create-hosted-zone \
                --name "$DOMAIN_NAME" \
                --caller-reference "$(date +%s)" \
                --query 'HostedZone.Id' \
                --output text)
            
            echo -e "${GREEN}✓ Created hosted zone for: $DOMAIN_NAME${NC}"
            echo -e "${YELLOW}⚠️  Update your domain's nameservers to:${NC}"
            
            aws route53 get-hosted-zone \
                --id "$ZONE_ID" \
                --query 'DelegationSet.NameServers' \
                --output table
        else
            echo "Hosted zone already exists for: $DOMAIN_NAME"
        fi
        
        # Save domain configuration
        echo "DOMAIN_NAME=$DOMAIN_NAME" > .env.production
        echo "HOSTED_ZONE_ID=$ZONE_ID" >> .env.production
    fi
}

# Initialize Terraform
initialize_terraform() {
    echo -e "\n${YELLOW}Initializing Terraform...${NC}"
    
    cd infrastructure
    
    # Create backend configuration
    cat > backend.tf <<EOF
terraform {
  backend "s3" {
    bucket         = "${PROJECT_NAME}-terraform-state-${AWS_REGION}"
    key            = "${ENVIRONMENT}/terraform.tfstate"
    region         = "${AWS_REGION}"
    dynamodb_table = "${PROJECT_NAME}-terraform-locks"
    encrypt        = true
  }
}
EOF
    
    # Create terraform.tfvars
    cat > terraform.tfvars <<EOF
# Auto-generated Terraform variables
environment = "${ENVIRONMENT}"
aws_region = "${AWS_REGION}"
project_name = "${PROJECT_NAME}"

# Update these values as needed
vpc_cidr = "10.0.0.0/16"
availability_zones = ["${AWS_REGION}a", "${AWS_REGION}b", "${AWS_REGION}c"]

# Compute settings
lambda_memory_size = 3008
lambda_timeout = 300

# Domain settings (update if you have a domain)
# domain_name = "serveml.com"
# certificate_arn = "arn:aws:acm:${AWS_REGION}:xxxx:certificate/yyyy"
EOF
    
    # Initialize Terraform
    terraform init
    
    echo -e "${GREEN}✓ Terraform initialized${NC}"
    
    cd ..
}

# Create IAM user for GitHub Actions
create_github_user() {
    echo -e "\n${YELLOW}Creating IAM user for GitHub Actions...${NC}"
    
    USER_NAME="${PROJECT_NAME}-github-actions"
    
    # Create user
    if aws iam get-user --user-name "$USER_NAME" &> /dev/null; then
        echo "IAM user already exists: $USER_NAME"
    else
        aws iam create-user --user-name "$USER_NAME"
        
        # Create access key
        CREDENTIALS=$(aws iam create-access-key --user-name "$USER_NAME" --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text)
        ACCESS_KEY=$(echo "$CREDENTIALS" | cut -f1)
        SECRET_KEY=$(echo "$CREDENTIALS" | cut -f2)
        
        echo -e "${GREEN}✓ Created IAM user: $USER_NAME${NC}"
        echo -e "${YELLOW}GitHub Secrets to add:${NC}"
        echo "AWS_ACCESS_KEY_ID: $ACCESS_KEY"
        echo "AWS_SECRET_ACCESS_KEY: $SECRET_KEY"
        echo -e "${RED}⚠️  Save these credentials securely! They won't be shown again.${NC}"
        
        # Save to local file (temporary)
        cat > github_secrets.txt <<EOF
Add these secrets to your GitHub repository:
https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/settings/secrets/actions

AWS_ACCESS_KEY_ID=$ACCESS_KEY
AWS_SECRET_ACCESS_KEY=$SECRET_KEY
AWS_REGION=$AWS_REGION
EOF
    fi
    
    # Attach necessary policies
    POLICY_ARNS=(
        "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess"
        "arn:aws:iam::aws:policy/AWSLambda_FullAccess"
        "arn:aws:iam::aws:policy/AmazonS3FullAccess"
        "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
    )
    
    for policy in "${POLICY_ARNS[@]}"; do
        aws iam attach-user-policy \
            --user-name "$USER_NAME" \
            --policy-arn "$policy" || true
    done
}

# Create initial monitoring dashboard
create_monitoring() {
    echo -e "\n${YELLOW}Creating CloudWatch dashboard...${NC}"
    
    DASHBOARD_NAME="${PROJECT_NAME}-${ENVIRONMENT}-overview"
    
    # Create dashboard JSON
    cat > dashboard.json <<'EOF'
{
    "widgets": [
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["ServeML/API", "RequestCount", {"stat": "Sum"}],
                    ["...", {"stat": "Average"}]
                ],
                "period": 300,
                "stat": "Average",
                "region": "REGION_PLACEHOLDER",
                "title": "API Request Count"
            }
        },
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AWS/Lambda", "Errors", {"stat": "Sum"}],
                    [".", "Duration", {"stat": "Average"}]
                ],
                "period": 300,
                "stat": "Average",
                "region": "REGION_PLACEHOLDER",
                "title": "Lambda Performance"
            }
        }
    ]
}
EOF
    
    # Replace region placeholder
    sed -i.bak "s/REGION_PLACEHOLDER/$AWS_REGION/g" dashboard.json
    
    # Create dashboard
    aws cloudwatch put-dashboard \
        --dashboard-name "$DASHBOARD_NAME" \
        --dashboard-body file://dashboard.json \
        --region "$AWS_REGION" || true
    
    rm dashboard.json dashboard.json.bak
    
    echo -e "${GREEN}✓ Created CloudWatch dashboard${NC}"
}

# Summary
print_summary() {
    echo -e "\n${GREEN}================================================${NC}"
    echo -e "${GREEN}     AWS Setup Complete!${NC}"
    echo -e "${GREEN}================================================${NC}"
    
    echo -e "\n${YELLOW}Next Steps:${NC}"
    echo "1. Review and update infrastructure/terraform.tfvars"
    echo "2. Add GitHub secrets from github_secrets.txt"
    echo "3. Run: cd infrastructure && terraform plan"
    echo "4. Deploy infrastructure: terraform apply"
    echo "5. Build and push Docker images"
    echo "6. Deploy the application"
    
    echo -e "\n${YELLOW}Important Files Created:${NC}"
    echo "- infrastructure/backend.tf (Terraform backend config)"
    echo "- infrastructure/terraform.tfvars (Terraform variables)"
    echo "- .env.production (Production environment variables)"
    echo "- github_secrets.txt (GitHub Actions secrets)"
    
    echo -e "\n${YELLOW}AWS Resources Created:${NC}"
    echo "- S3 bucket for Terraform state"
    echo "- DynamoDB table for state locking"
    echo "- ECR repositories for Docker images"
    echo "- KMS key for secrets encryption"
    echo "- SSM parameters for secrets"
    echo "- IAM user for GitHub Actions"
    echo "- CloudWatch dashboard"
    
    if [ -f ".env.production" ]; then
        echo -e "\n${YELLOW}Domain Configuration:${NC}"
        cat .env.production
    fi
}

# Main execution
main() {
    echo "This script will set up AWS resources for ServeML deployment."
    echo "Region: $AWS_REGION"
    echo
    read -p "Continue? (y/n): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
    
    check_prerequisites
    create_terraform_backend
    create_ecr_repositories
    create_kms_keys
    create_secrets
    create_hosted_zone
    initialize_terraform
    create_github_user
    create_monitoring
    print_summary
}

# Run main function
main