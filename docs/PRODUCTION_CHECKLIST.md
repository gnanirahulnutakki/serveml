# ServeML Production Deployment Checklist

This checklist ensures a smooth and secure production deployment.

## Pre-Deployment Requirements

### 1. AWS Account Setup ✅
- [ ] AWS account created and verified
- [ ] Billing alerts configured
- [ ] MFA enabled on root account
- [ ] IAM users created with least privilege
- [ ] AWS CLI configured locally

### 2. Domain & SSL ✅
- [ ] Domain registered (serveml.com or alternative)
- [ ] Route 53 hosted zone created
- [ ] SSL certificate requested in ACM
- [ ] Certificate validated
- [ ] Domain nameservers updated

### 3. Security Preparation ✅
- [ ] All secrets generated and stored in AWS SSM
- [ ] KMS key created for encryption
- [ ] Security groups reviewed
- [ ] WAF rules configured
- [ ] GitHub secrets added

### 4. Code Readiness ✅
- [ ] All tests passing (run `cd tests && ./run_tests.sh`)
- [ ] Security vulnerabilities fixed
- [ ] Code reviewed and approved
- [ ] Documentation complete
- [ ] Version tagged in Git

## Infrastructure Deployment

### Phase 1: Core Infrastructure (Day 1)

```bash
cd infrastructure
terraform workspace new prod
terraform plan -out=tfplan
terraform apply tfplan
```

**Checklist:**
- [ ] VPC and networking created
- [ ] S3 buckets provisioned
- [ ] DynamoDB tables created
- [ ] ECR repositories created
- [ ] KMS keys configured
- [ ] IAM roles and policies applied

**Verification:**
```bash
# Verify VPC
aws ec2 describe-vpcs --filters "Name=tag:Project,Values=serveml"

# Verify S3 buckets
aws s3 ls | grep serveml

# Verify DynamoDB tables
aws dynamodb list-tables | grep serveml
```

### Phase 2: Backend Deployment (Day 1)

```bash
# Build and push Docker image
cd backend
docker build -t serveml-backend:prod .
docker tag serveml-backend:prod $ECR_REGISTRY/serveml-backend:latest
docker push $ECR_REGISTRY/serveml-backend:latest

# Deploy ECS service
aws ecs update-service --cluster serveml-prod --service backend --force-new-deployment
```

**Checklist:**
- [ ] Docker image built successfully
- [ ] Image pushed to ECR
- [ ] ECS task definition updated
- [ ] ECS service deployed
- [ ] Health checks passing
- [ ] Logs flowing to CloudWatch

**Verification:**
```bash
# Check ECS service
aws ecs describe-services --cluster serveml-prod --services backend

# Test API endpoint
curl https://api.serveml.com/health
```

### Phase 3: Frontend Deployment (Day 1)

```bash
cd frontend
npm install
npm run build
aws s3 sync dist/ s3://serveml-frontend-prod/ --delete
aws cloudfront create-invalidation --distribution-id $CF_DIST_ID --paths "/*"
```

**Checklist:**
- [ ] Frontend built without errors
- [ ] Assets uploaded to S3
- [ ] CloudFront distribution updated
- [ ] Cache invalidated
- [ ] Domain pointing to CloudFront
- [ ] SSL working correctly

**Verification:**
```bash
# Test frontend
curl -I https://serveml.com
curl -I https://app.serveml.com
```

### Phase 4: Lambda Functions (Day 2)

```bash
# Deploy model serving wrapper
cd backend/templates
./deploy_lambda.sh

# Deploy scheduled tasks
cd ../../lambdas
./deploy_all.sh
```

**Checklist:**
- [ ] Lambda functions created
- [ ] Environment variables set
- [ ] IAM roles attached
- [ ] Event triggers configured
- [ ] Dead letter queues set up
- [ ] X-Ray tracing enabled

## Post-Deployment Configuration

### 1. Monitoring Setup (Day 2)

**CloudWatch Dashboards:**
- [ ] API metrics dashboard created
- [ ] Lambda performance dashboard created
- [ ] Cost tracking dashboard created
- [ ] Custom metrics configured

**Alarms:**
- [ ] High error rate alarm (>1%)
- [ ] High latency alarm (>1s)
- [ ] Lambda failures alarm
- [ ] DynamoDB throttling alarm
- [ ] Budget alarm ($1000/month)

**Verification:**
```bash
# List dashboards
aws cloudwatch list-dashboards

# List alarms
aws cloudwatch describe-alarms --state-value OK
```

### 2. Security Validation (Day 2)

**Security Scan:**
```bash
# Run security audit
./scripts/security_audit.sh

# Check SSL configuration
nmap --script ssl-enum-ciphers -p 443 serveml.com

# Verify WAF is active
aws wafv2 get-web-acl --scope REGIONAL --id $WAF_ID
```

**Checklist:**
- [ ] SSL Labs score A or better
- [ ] Security headers configured
- [ ] WAF rules active
- [ ] Secrets not exposed in logs
- [ ] CORS properly configured

### 3. Performance Testing (Day 3)

```bash
# Run load tests
cd tests/load
locust --host https://api.serveml.com --users 100 --spawn-rate 10 --run-time 300s

# Run performance benchmarks
cd ../performance
python benchmark.py --production
```

**Success Criteria:**
- [ ] p95 latency < 500ms
- [ ] p99 latency < 1s
- [ ] 0% error rate under normal load
- [ ] Auto-scaling triggers correctly
- [ ] No memory leaks detected

### 4. Backup Configuration (Day 3)

**Automated Backups:**
- [ ] DynamoDB point-in-time recovery enabled
- [ ] S3 versioning enabled
- [ ] S3 lifecycle policies configured
- [ ] CloudWatch Logs retention set
- [ ] Backup Lambda function deployed

**Manual Backup Test:**
```bash
# Create manual backup
aws dynamodb create-backup --table-name serveml-deployments-prod --backup-name manual-test-backup

# Verify backup
aws dynamodb list-backups --table-name serveml-deployments-prod
```

## Go-Live Checklist

### Final Preparations (Day 4)

**Documentation:**
- [ ] API documentation live at docs.serveml.com
- [ ] User guide published
- [ ] Support email configured
- [ ] Status page set up

**Communication:**
- [ ] Team notified of go-live
- [ ] Support channels ready
- [ ] Monitoring alerts configured
- [ ] On-call schedule set

### DNS Cutover (Day 4)

```bash
# Update DNS records to production
aws route53 change-resource-record-sets --hosted-zone-id $ZONE_ID --change-batch file://dns-cutover.json
```

**Checklist:**
- [ ] DNS TTL reduced to 60s (24 hours before)
- [ ] DNS records updated
- [ ] Propagation verified globally
- [ ] Old infrastructure still running
- [ ] Traffic monitoring active

### Launch Day (Day 5)

**Morning Checks:**
- [ ] All systems green on dashboard
- [ ] No critical alerts overnight
- [ ] Team available and ready
- [ ] Rollback plan reviewed

**Launch Steps:**
1. [ ] Enable production traffic (remove maintenance page)
2. [ ] Monitor real-time metrics
3. [ ] Check error rates
4. [ ] Verify user registrations working
5. [ ] Test model deployment flow
6. [ ] Monitor auto-scaling

**Success Metrics (First 24 Hours):**
- [ ] < 0.1% error rate
- [ ] < 500ms p95 latency
- [ ] No critical incidents
- [ ] Successful user registrations
- [ ] At least 10 model deployments

## Post-Launch Activities

### Week 1
- [ ] Daily metrics review
- [ ] User feedback collection
- [ ] Performance optimization
- [ ] Cost analysis
- [ ] Security audit

### Week 2
- [ ] First production backup test
- [ ] Disaster recovery drill
- [ ] Load testing at 2x capacity
- [ ] Documentation updates
- [ ] Team retrospective

### Month 1
- [ ] Full security penetration test
- [ ] Cost optimization review
- [ ] Performance baseline establishment
- [ ] SLA metrics calculation
- [ ] Roadmap planning

## Rollback Plan

If critical issues arise:

### Immediate Rollback (< 5 minutes)
```bash
# Revert DNS
aws route53 change-resource-record-sets --hosted-zone-id $ZONE_ID --change-batch file://dns-rollback.json

# Stop new deployments
aws ecs update-service --cluster serveml-prod --service backend --desired-count 0
```

### Full Rollback (< 30 minutes)
```bash
# Restore from backup
./scripts/restore_production.sh --timestamp $BACKUP_TIME

# Redeploy previous version
git checkout $PREVIOUS_TAG
./scripts/deploy_all.sh --emergency
```

## Emergency Contacts

**On-Call Rotation:**
- Primary: [Name] - [Phone]
- Secondary: [Name] - [Phone]
- Manager: [Name] - [Phone]

**AWS Support:**
- Case URL: https://console.aws.amazon.com/support
- Phone: [AWS Support Number]
- Severity: P1 for production down

**External Services:**
- Domain Registrar: [Support Contact]
- Email Provider: [Support Contact]
- Monitoring: [Support Contact]

## Sign-Off

**Pre-Production:**
- [ ] Engineering Lead: _________________ Date: _______
- [ ] Security Lead: ___________________ Date: _______
- [ ] Operations Lead: _________________ Date: _______

**Production Launch:**
- [ ] CTO/VP Engineering: ______________ Date: _______
- [ ] Product Manager: _________________ Date: _______

**Post-Launch Review:**
- [ ] All Systems Operational: __________ Date: _______
- [ ] SLA Targets Met: _________________ Date: _______

---

**Notes Section:**
_Use this space to document any deviations from the plan, issues encountered, or lessons learned._

_____________________________________________________________
_____________________________________________________________
_____________________________________________________________