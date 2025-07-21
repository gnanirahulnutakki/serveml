# ServeML Monitoring & Alerting Guide

This guide covers comprehensive monitoring, alerting, and observability for ServeML in production.

## Table of Contents

1. [Overview](#overview)
2. [Metrics Collection](#metrics-collection)
3. [CloudWatch Setup](#cloudwatch-setup)
4. [Custom Metrics](#custom-metrics)
5. [Alerting Rules](#alerting-rules)
6. [Dashboards](#dashboards)
7. [Log Analysis](#log-analysis)
8. [Distributed Tracing](#distributed-tracing)
9. [Incident Response](#incident-response)

## Overview

### Monitoring Stack

- **Metrics**: CloudWatch, Prometheus
- **Logs**: CloudWatch Logs, ElasticSearch
- **Traces**: AWS X-Ray
- **Alerts**: CloudWatch Alarms, SNS, PagerDuty
- **Dashboards**: CloudWatch, Grafana

### Key Performance Indicators (KPIs)

1. **Availability**: 99.9% uptime target
2. **Latency**: p95 < 500ms, p99 < 1s
3. **Error Rate**: < 0.1%
4. **Deployment Success Rate**: > 95%
5. **Cost per Deployment**: < $0.10

## Metrics Collection

### Application Metrics

```python
# backend/metrics.py
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

def publish_metric(namespace, metric_name, value, unit='Count', dimensions=None):
    """Publish custom metric to CloudWatch"""
    metric_data = {
        'MetricName': metric_name,
        'Value': value,
        'Unit': unit,
        'Timestamp': datetime.utcnow()
    }
    
    if dimensions:
        metric_data['Dimensions'] = [
            {'Name': k, 'Value': v} for k, v in dimensions.items()
        ]
    
    cloudwatch.put_metric_data(
        Namespace=namespace,
        MetricData=[metric_data]
    )

# Usage in application
publish_metric(
    'ServeML/API',
    'DeploymentCreated',
    1,
    dimensions={'Environment': 'prod', 'Framework': 'sklearn'}
)
```

### Infrastructure Metrics

```bash
# Enable detailed monitoring for EC2/ECS
aws ec2 modify-instance-attribute \
  --instance-id i-1234567890abcdef0 \
  --monitoring Enabled=true

# Enable Container Insights
aws ecs put-account-setting \
  --name containerInsights \
  --value enabled
```

## CloudWatch Setup

### 1. Create Custom Namespace

```bash
# Custom metrics namespace
aws cloudwatch put-metric-data \
  --namespace ServeML/Production \
  --metric-name TestMetric \
  --value 1
```

### 2. Log Groups Configuration

```bash
# Create log groups with retention
for group in api lambda deployments; do
  aws logs create-log-group \
    --log-group-name /serveml/prod/$group
  
  aws logs put-retention-policy \
    --log-group-name /serveml/prod/$group \
    --retention-in-days 30
done

# Create metric filters
aws logs put-metric-filter \
  --log-group-name /serveml/prod/api \
  --filter-name errors \
  --filter-pattern '[timestamp, request_id, level=ERROR, ...]' \
  --metric-transformations \
    metricName=ErrorCount,\
    metricNamespace=ServeML/API,\
    metricValue=1
```

### 3. CloudWatch Agent Configuration

```json
{
  "metrics": {
    "namespace": "ServeML/System",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {"name": "cpu_usage_idle", "rename": "CPU_IDLE", "unit": "Percent"},
          {"name": "cpu_usage_iowait", "rename": "CPU_IOWAIT", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": [
          {"name": "used_percent", "rename": "DISK_USED", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60,
        "resources": ["*"]
      },
      "mem": {
        "measurement": [
          {"name": "mem_used_percent", "rename": "MEM_USED", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/serveml/app.log",
            "log_group_name": "/serveml/prod/api",
            "log_stream_name": "{instance_id}",
            "timezone": "UTC"
          }
        ]
      }
    }
  }
}
```

## Custom Metrics

### 1. Business Metrics

```python
# Track deployment metrics
class DeploymentMetrics:
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = 'ServeML/Business'
    
    def track_deployment(self, user_id, framework, model_size_mb, duration_seconds):
        metrics = [
            {
                'MetricName': 'DeploymentCount',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Framework', 'Value': framework}
                ]
            },
            {
                'MetricName': 'ModelSize',
                'Value': model_size_mb,
                'Unit': 'Megabytes',
                'Dimensions': [
                    {'Name': 'Framework', 'Value': framework}
                ]
            },
            {
                'MetricName': 'DeploymentDuration',
                'Value': duration_seconds,
                'Unit': 'Seconds',
                'Dimensions': [
                    {'Name': 'Framework', 'Value': framework}
                ]
            }
        ]
        
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=metrics
        )
```

### 2. Performance Metrics

```python
# Track API performance
from functools import wraps
import time

def track_performance(metric_name):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                status = 'success'
                return result
            except Exception as e:
                status = 'error'
                raise
            finally:
                duration = time.time() - start_time
                publish_metric(
                    'ServeML/API',
                    f'{metric_name}_duration',
                    duration * 1000,  # Convert to milliseconds
                    unit='Milliseconds',
                    dimensions={'Status': status}
                )
        return wrapper
    return decorator

# Usage
@track_performance('deploy_model')
async def deploy_model(request):
    # Implementation
    pass
```

## Alerting Rules

### 1. Critical Alerts

```bash
# High error rate
aws cloudwatch put-metric-alarm \
  --alarm-name "ServeML-HighErrorRate" \
  --alarm-description "API error rate above 1%" \
  --namespace "AWS/ApiGateway" \
  --metric-name "4XXError" \
  --dimensions Name=ApiName,Value=ServeML-API \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:serveml-critical

# Lambda failures
aws cloudwatch put-metric-alarm \
  --alarm-name "ServeML-LambdaFailures" \
  --namespace "AWS/Lambda" \
  --metric-name "Errors" \
  --dimensions Name=FunctionName,Value=serveml-model-serving \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 3 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

### 2. Warning Alerts

```bash
# High latency
aws cloudwatch put-metric-alarm \
  --alarm-name "ServeML-HighLatency" \
  --namespace "AWS/ApiGateway" \
  --metric-name "Latency" \
  --dimensions Name=ApiName,Value=ServeML-API \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:serveml-warning

# DynamoDB throttling
aws cloudwatch put-metric-alarm \
  --alarm-name "ServeML-DynamoDBThrottled" \
  --namespace "AWS/DynamoDB" \
  --metric-name "UserErrors" \
  --dimensions Name=TableName,Value=serveml-deployments \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

### 3. Cost Alerts

```bash
# Monthly budget alert
aws budgets create-budget \
  --account-id 123456789012 \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json

# budget.json
{
  "BudgetName": "ServeML-Monthly",
  "BudgetLimit": {
    "Amount": "5000",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
```

## Dashboards

### 1. CloudWatch Dashboard

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["ServeML/API", "RequestCount", {"stat": "Sum"}],
          [".", "ErrorCount", {"stat": "Sum"}],
          ["AWS/ApiGateway", "Count", {"stat": "Sum"}],
          [".", "4XXError", {"stat": "Sum"}],
          [".", "5XXError", {"stat": "Sum"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "API Metrics"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Invocations", {"stat": "Sum"}],
          [".", "Errors", {"stat": "Sum"}],
          [".", "Duration", {"stat": "Average"}],
          [".", "ConcurrentExecutions", {"stat": "Maximum"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Lambda Performance"
      }
    }
  ]
}
```

### 2. Grafana Dashboard

```yaml
# docker-compose.yml for Grafana
version: '3.8'
services:
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_AWS_default_REGION=us-east-1
    volumes:
      - grafana-storage:/var/lib/grafana
      - ./dashboards:/etc/grafana/provisioning/dashboards
      - ./datasources:/etc/grafana/provisioning/datasources

volumes:
  grafana-storage:
```

## Log Analysis

### 1. CloudWatch Insights Queries

```sql
-- Top errors by endpoint
fields @timestamp, method, path, status_code, error_message
| filter status_code >= 400
| stats count() by path
| sort count desc

-- Deployment duration analysis
fields @timestamp, deployment_id, duration_ms
| filter @message like /Deployment completed/
| stats avg(duration_ms), min(duration_ms), max(duration_ms) by bin(1h)

-- User activity
fields @timestamp, user_id, action
| filter action in ["deploy", "delete", "test"]
| stats count() by user_id, action
```

### 2. Log Aggregation Pipeline

```python
# Log processor Lambda
import json
import gzip
import base64
import boto3

def process_logs(event, context):
    """Process CloudWatch logs for analysis"""
    
    # Decode the log data
    log_data = json.loads(
        gzip.decompress(
            base64.b64decode(event['awslogs']['data'])
        )
    )
    
    # Extract and process log events
    for log_event in log_data['logEvents']:
        message = log_event['message']
        
        # Parse structured logs
        try:
            log_entry = json.loads(message)
            
            # Send to ElasticSearch or S3
            if log_entry.get('level') == 'ERROR':
                send_to_elasticsearch(log_entry)
            
            # Track metrics
            if log_entry.get('action') == 'deployment_completed':
                track_deployment_metric(log_entry)
                
        except json.JSONDecodeError:
            # Handle unstructured logs
            pass
```

## Distributed Tracing

### 1. X-Ray Configuration

```python
# Enable X-Ray tracing in FastAPI
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

# Configure X-Ray
xray_recorder.configure(
    context_missing='LOG_ERROR',
    plugins=('EC2Plugin', 'ECSPlugin'),
    daemon_address='127.0.0.1:2000'
)

# Add middleware
app.add_middleware(XRayMiddleware, recorder=xray_recorder)

# Trace custom segments
@xray_recorder.capture('deploy_model')
async def deploy_model(request):
    # Add metadata
    subsegment = xray_recorder.current_subsegment()
    subsegment.put_metadata('model_size', model_size)
    subsegment.put_annotation('framework', framework)
    
    # Implementation
    pass
```

### 2. Service Map Analysis

```bash
# Get service statistics
aws xray get-service-statistics \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S)

# Get trace summaries
aws xray get-trace-summaries \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --filter-expression "service(\"serveml-api\") AND responseTime > 1"
```

## Incident Response

### 1. Runbooks

#### High Error Rate Runbook

```markdown
## Alarm: ServeML-HighErrorRate

### Symptoms
- API error rate > 1%
- Users reporting failures

### Investigation Steps
1. Check CloudWatch dashboard for error patterns
2. Query recent errors:
   ```
   aws logs filter-log-events \
     --log-group-name /serveml/prod/api \
     --filter-pattern "ERROR"
   ```
3. Check upstream dependencies (DynamoDB, S3, Lambda)
4. Review recent deployments

### Mitigation
1. If code issue: Rollback to previous version
2. If capacity issue: Scale up instances
3. If dependency issue: Implement circuit breaker

### Escalation
- L1: On-call engineer (0-30 min)
- L2: Team lead (30-60 min)
- L3: Platform architect (60+ min)
```

### 2. Automation Scripts

```python
# automated_response.py
import boto3
import json
from datetime import datetime, timedelta

class IncidentResponder:
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.ecs = boto3.client('ecs')
        self.sns = boto3.client('sns')
    
    def handle_high_error_rate(self, alarm_name):
        """Automated response to high error rate"""
        
        # 1. Gather diagnostics
        metrics = self.get_error_metrics()
        
        # 2. Check if auto-scaling would help
        if self.is_capacity_issue(metrics):
            self.scale_up_service()
            self.notify_team("Auto-scaled ECS service due to high error rate")
            return
        
        # 3. Check if circuit breaker should activate
        if metrics['error_rate'] > 0.5:  # 50% error rate
            self.enable_circuit_breaker()
            self.notify_team("Circuit breaker activated due to extreme error rate")
            return
        
        # 4. Escalate to humans
        self.page_on_call("High error rate requires manual intervention")
    
    def get_error_metrics(self):
        """Get recent error metrics"""
        response = self.cloudwatch.get_metric_statistics(
            Namespace='ServeML/API',
            MetricName='ErrorRate',
            StartTime=datetime.utcnow() - timedelta(minutes=10),
            EndTime=datetime.utcnow(),
            Period=60,
            Statistics=['Average', 'Maximum']
        )
        return {
            'error_rate': max(dp['Maximum'] for dp in response['Datapoints']),
            'datapoints': response['Datapoints']
        }
```

### 3. Post-Incident Review Template

```markdown
## Incident Post-Mortem

**Incident ID**: INC-2024-001
**Date**: 2024-01-15
**Duration**: 45 minutes
**Severity**: P1

### Summary
Brief description of what happened

### Timeline
- 14:00 - First alert triggered
- 14:05 - On-call engineer acknowledged
- 14:15 - Root cause identified
- 14:30 - Fix deployed
- 14:45 - Service fully recovered

### Root Cause
Detailed explanation of the root cause

### Impact
- Number of affected users
- Failed deployments
- Revenue impact

### Action Items
1. [ ] Implement additional monitoring
2. [ ] Add input validation
3. [ ] Update runbook
4. [ ] Schedule team training

### Lessons Learned
- What went well
- What could be improved
- Process improvements
```

## Monitoring Best Practices

### 1. Alert Fatigue Prevention
- Set appropriate thresholds
- Use composite alarms
- Implement alert routing
- Regular alert review

### 2. Dashboard Design
- One screen visibility
- Logical grouping
- Color coding for severity
- Include business metrics

### 3. Log Management
- Structured logging
- Consistent format
- Appropriate retention
- Cost optimization

### 4. Performance Optimization
- Sample high-volume metrics
- Use metric math
- Aggregate before sending
- Archive old data

## Tools and Resources

### Monitoring Tools
- [CloudWatch](https://aws.amazon.com/cloudwatch/)
- [X-Ray](https://aws.amazon.com/xray/)
- [Grafana](https://grafana.com/)
- [Prometheus](https://prometheus.io/)

### Learning Resources
- [AWS Observability Best Practices](https://aws-observability.github.io/observability-best-practices/)
- [SRE Workbook](https://sre.google/workbook/table-of-contents/)
- [Distributed Systems Observability](https://www.oreilly.com/library/view/distributed-systems-observability/9781492033431/)