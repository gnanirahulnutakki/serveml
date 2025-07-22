# ServeML Domain Setup Guide

This guide walks through registering and configuring a domain for ServeML.

## Domain Registration Options

### Option 1: AWS Route 53 (Recommended)

**Pros:**
- Integrated with AWS services
- Automatic SSL certificate validation
- Easy DNS management
- Health checks and failover

**Steps:**

1. **Register Domain via Route 53**
   ```bash
   # Check domain availability
   aws route53domains check-domain-availability --domain-name serveml.com
   
   # Register domain (requires additional setup)
   # Use AWS Console: https://console.aws.amazon.com/route53/domains
   ```

2. **Estimated Costs:**
   - `.com` domain: $12/year
   - `.io` domain: $32/year
   - `.dev` domain: $12/year
   - `.ai` domain: $75/year

### Option 2: External Registrar

**Popular Registrars:**
- Namecheap (~$10-15/year for .com)
- Google Domains (~$12/year for .com)
- Cloudflare Registrar (at-cost pricing)
- GoDaddy (~$12-20/year for .com)

**Steps:**

1. Register domain at chosen registrar
2. Update nameservers to Route 53:
   ```
   ns-123.awsdns-12.com
   ns-456.awsdns-34.net
   ns-789.awsdns-56.co.uk
   ns-012.awsdns-78.org
   ```

## Domain Configuration

### 1. Create Hosted Zone

```bash
# Create hosted zone in Route 53
aws route53 create-hosted-zone \
  --name serveml.com \
  --caller-reference "$(date +%s)" \
  --hosted-zone-config Comment="ServeML production domain"

# Get nameservers
aws route53 get-hosted-zone \
  --id /hostedzone/Z1234567890ABC \
  --query 'DelegationSet.NameServers'
```

### 2. SSL Certificate Setup

```bash
# Request ACM certificate
aws acm request-certificate \
  --domain-name serveml.com \
  --subject-alternative-names "*.serveml.com" "api.serveml.com" "app.serveml.com" \
  --validation-method DNS \
  --region us-east-1  # Must be us-east-1 for CloudFront

# Get validation records
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123 \
  --query 'Certificate.DomainValidationOptions'
```

### 3. DNS Records Configuration

```hcl
# terraform/dns.tf
resource "aws_route53_record" "root" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "serveml.com"
  type    = "A"
  
  alias {
    name                   = aws_cloudfront_distribution.frontend.domain_name
    zone_id                = aws_cloudfront_distribution.frontend.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "www" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "www.serveml.com"
  type    = "CNAME"
  ttl     = 300
  records = ["serveml.com"]
}

resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.serveml.com"
  type    = "A"
  
  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "app" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "app.serveml.com"
  type    = "A"
  
  alias {
    name                   = aws_cloudfront_distribution.app.domain_name
    zone_id                = aws_cloudfront_distribution.app.hosted_zone_id
    evaluate_target_health = false
  }
}
```

## Subdomain Structure

```
serveml.com              → Marketing website / Landing page
app.serveml.com          → Main application (React frontend)
api.serveml.com          → REST API endpoints
docs.serveml.com         → Documentation site
status.serveml.com       → Status page
blog.serveml.com         → Blog (optional)
```

## Email Configuration

### Option 1: AWS SES (Simple Email Service)

```bash
# Verify domain for sending
aws ses verify-domain-identity --domain serveml.com

# Get verification token
aws ses get-identity-verification-attributes \
  --identities serveml.com

# Add TXT record for verification
_amazonses.serveml.com TXT "verification-token-here"
```

### Option 2: External Email Providers

**Google Workspace:**
- $6/user/month
- Professional email: team@serveml.com

**Zoho Mail:**
- $1/user/month
- More affordable option

**ProtonMail:**
- $5/user/month
- Privacy-focused

### Email DNS Records

```bash
# MX Records for Google Workspace
serveml.com MX 1 aspmx.l.google.com
serveml.com MX 5 alt1.aspmx.l.google.com
serveml.com MX 5 alt2.aspmx.l.google.com
serveml.com MX 10 alt3.aspmx.l.google.com
serveml.com MX 10 alt4.aspmx.l.google.com

# SPF Record
serveml.com TXT "v=spf1 include:_spf.google.com ~all"

# DKIM (get from email provider)
google._domainkey.serveml.com TXT "v=DKIM1; k=rsa; p=..."

# DMARC
_dmarc.serveml.com TXT "v=DMARC1; p=quarantine; rua=mailto:dmarc@serveml.com"
```

## Domain Security

### 1. DNSSEC Setup

```bash
# Enable DNSSEC
aws route53 enable-hosted-zone-dnssec \
  --hosted-zone-id Z1234567890ABC

# Get DS record for registrar
aws route53 get-dnssec \
  --hosted-zone-id Z1234567890ABC
```

### 2. CAA Records

```bash
# Only allow AWS and Let's Encrypt to issue certificates
serveml.com CAA 0 issue "amazon.com"
serveml.com CAA 0 issue "letsencrypt.org"
serveml.com CAA 0 iodef "mailto:security@serveml.com"
```

### 3. Security Headers

Configure CloudFront to add security headers:

```json
{
  "Headers": {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' https://api.serveml.com; style-src 'self' 'unsafe-inline';"
  }
}
```

## Alternative Domain Names

If `serveml.com` is taken, consider:

### Available Alternatives (as of writing):
- `serveml.io` - Good for tech projects
- `serveml.ai` - AI/ML focused
- `serveml.dev` - Developer-friendly
- `serveml.cloud` - Cloud-focused
- `serveml.app` - Application-focused
- `serve-ml.com` - Hyphenated version
- `servemldeploy.com` - Descriptive
- `deployml.com` - Alternative name
- `mlserve.com` - Reversed
- `quickml.com` - Emphasizes speed

### Domain Selection Criteria:
1. **Memorable** - Easy to remember and spell
2. **Short** - Preferably under 10 characters
3. **Relevant** - Related to ML/deployment
4. **Available** - Check social media handles too
5. **No trademark conflicts** - Search USPTO database

## Cost Summary

### Initial Setup (Year 1):
- Domain registration: $12-75/year
- SSL Certificate: Free (AWS ACM)
- Route 53 Hosted Zone: $0.50/month
- Email (optional): $1-6/user/month

### Ongoing Costs:
- Domain renewal: $12-75/year
- DNS queries: ~$0.40 per million queries
- Email service: $12-72/user/year

### Total Estimated Cost:
- **Basic setup**: ~$20/year (domain + DNS)
- **Professional setup**: ~$100/year (includes email)

## Quick Setup Script

```bash
#!/bin/bash
# Quick domain setup for ServeML

DOMAIN="serveml.com"
EMAIL="admin@serveml.com"

# Create hosted zone
ZONE_ID=$(aws route53 create-hosted-zone \
  --name $DOMAIN \
  --caller-reference "$(date +%s)" \
  --query 'HostedZone.Id' \
  --output text)

echo "Hosted Zone ID: $ZONE_ID"

# Request certificate
CERT_ARN=$(aws acm request-certificate \
  --domain-name $DOMAIN \
  --subject-alternative-names "*.$DOMAIN" \
  --validation-method DNS \
  --region us-east-1 \
  --query 'CertificateArn' \
  --output text)

echo "Certificate ARN: $CERT_ARN"

# Output nameservers
echo "Update your domain registrar with these nameservers:"
aws route53 get-hosted-zone \
  --id $ZONE_ID \
  --query 'DelegationSet.NameServers' \
  --output table
```

## Next Steps

1. **Choose and register domain**
2. **Set up Route 53 hosted zone**
3. **Request SSL certificate**
4. **Configure DNS records**
5. **Set up email (optional)**
6. **Update application configuration**
7. **Test domain resolution**

## Troubleshooting

### DNS Propagation
- Use `dig` or `nslookup` to verify:
  ```bash
  dig serveml.com
  nslookup serveml.com
  ```

### Certificate Validation
- Check validation status:
  ```bash
  aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --query 'Certificate.Status'
  ```

### Email Deliverability
- Test with mail-tester.com
- Check SPF/DKIM/DMARC alignment
- Monitor bounce rates