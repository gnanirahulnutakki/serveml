"""
Metrics and monitoring service for ServeML
"""
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class MetricsService:
    """Handle metrics collection and retrieval"""
    
    def __init__(self, table_name: str = "serveml-metrics"):
        self.dynamodb = boto3.resource('dynamodb')
        self.cloudwatch = boto3.client('cloudwatch')
        self.table_name = table_name
        
        # In-memory metrics buffer for batching
        self.metrics_buffer = defaultdict(list)
    
    def record_deployment_metric(
        self,
        deployment_id: str,
        metric_type: str,
        value: float,
        unit: str = 'Count',
        metadata: Optional[Dict] = None
    ):
        """Record a deployment metric"""
        try:
            timestamp = datetime.utcnow()
            
            # Add to buffer for batch processing
            self.metrics_buffer[deployment_id].append({
                'timestamp': timestamp.isoformat(),
                'metric_type': metric_type,
                'value': value,
                'unit': unit,
                'metadata': metadata or {}
            })
            
            # Send to CloudWatch
            self.cloudwatch.put_metric_data(
                Namespace='ServeML/Deployments',
                MetricData=[
                    {
                        'MetricName': metric_type,
                        'Dimensions': [
                            {
                                'Name': 'DeploymentId',
                                'Value': deployment_id
                            }
                        ],
                        'Value': value,
                        'Unit': unit,
                        'Timestamp': timestamp
                    }
                ]
            )
            
            # Flush buffer if it gets too large
            if len(self.metrics_buffer[deployment_id]) > 100:
                self.flush_metrics(deployment_id)
                
        except Exception as e:
            logger.error(f"Error recording metric: {e}")
    
    def record_prediction_metrics(
        self,
        deployment_id: str,
        latency_ms: float,
        success: bool,
        input_size: int,
        output_size: int
    ):
        """Record metrics for a prediction request"""
        # Record latency
        self.record_deployment_metric(
            deployment_id=deployment_id,
            metric_type='PredictionLatency',
            value=latency_ms,
            unit='Milliseconds'
        )
        
        # Record success/failure
        self.record_deployment_metric(
            deployment_id=deployment_id,
            metric_type='PredictionSuccess' if success else 'PredictionError',
            value=1,
            unit='Count'
        )
        
        # Record data sizes
        self.record_deployment_metric(
            deployment_id=deployment_id,
            metric_type='InputSize',
            value=input_size,
            unit='Bytes'
        )
        
        self.record_deployment_metric(
            deployment_id=deployment_id,
            metric_type='OutputSize',
            value=output_size,
            unit='Bytes'
        )
    
    def get_deployment_metrics(
        self,
        deployment_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        metric_names: Optional[List[str]] = None
    ) -> Dict:
        """Get metrics for a deployment"""
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=24)
        
        if not end_time:
            end_time = datetime.utcnow()
        
        if not metric_names:
            metric_names = [
                'PredictionLatency',
                'PredictionSuccess',
                'PredictionError',
                'InputSize',
                'OutputSize'
            ]
        
        metrics = {}
        
        try:
            for metric_name in metric_names:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace='ServeML/Deployments',
                    MetricName=metric_name,
                    Dimensions=[
                        {
                            'Name': 'DeploymentId',
                            'Value': deployment_id
                        }
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,  # 5 minutes
                    Statistics=['Average', 'Sum', 'Maximum', 'Minimum', 'SampleCount']
                )
                
                metrics[metric_name] = response['Datapoints']
            
            # Calculate derived metrics
            metrics['summary'] = self._calculate_summary_stats(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {}
    
    def _calculate_summary_stats(self, metrics: Dict) -> Dict:
        """Calculate summary statistics from raw metrics"""
        summary = {
            'total_requests': 0,
            'success_rate': 0,
            'average_latency': 0,
            'p99_latency': 0,
            'total_errors': 0
        }
        
        # Calculate total requests
        if 'PredictionSuccess' in metrics:
            success_points = metrics['PredictionSuccess']
            summary['total_requests'] += sum(p.get('Sum', 0) for p in success_points)
        
        if 'PredictionError' in metrics:
            error_points = metrics['PredictionError']
            total_errors = sum(p.get('Sum', 0) for p in error_points)
            summary['total_errors'] = total_errors
            summary['total_requests'] += total_errors
        
        # Calculate success rate
        if summary['total_requests'] > 0:
            summary['success_rate'] = (
                (summary['total_requests'] - summary['total_errors']) / 
                summary['total_requests'] * 100
            )
        
        # Calculate latency stats
        if 'PredictionLatency' in metrics:
            latency_points = metrics['PredictionLatency']
            if latency_points:
                latencies = [p.get('Average', 0) for p in latency_points if p.get('Average')]
                if latencies:
                    summary['average_latency'] = sum(latencies) / len(latencies)
                    summary['p99_latency'] = sorted(latencies)[int(len(latencies) * 0.99)]
        
        return summary
    
    def get_usage_stats(self, user_id: str) -> Dict:
        """Get usage statistics for a user"""
        # In production, query from DynamoDB
        # For MVP, return mock data
        return {
            'total_deployments': 5,
            'active_deployments': 3,
            'total_predictions': 10000,
            'total_compute_time_ms': 500000,
            'storage_used_mb': 250,
            'bandwidth_used_gb': 2.5
        }
    
    def create_dashboard_link(self, deployment_id: str) -> str:
        """Create CloudWatch dashboard link for deployment"""
        # In production, create a pre-configured dashboard
        region = boto3.Session().region_name
        return (
            f"https://console.aws.amazon.com/cloudwatch/home?"
            f"region={region}#dashboards:name=ServeML-{deployment_id}"
        )
    
    def flush_metrics(self, deployment_id: str):
        """Flush metrics buffer to persistent storage"""
        if deployment_id not in self.metrics_buffer:
            return
        
        try:
            # In production, write to DynamoDB or S3
            metrics_data = self.metrics_buffer[deployment_id]
            
            # Clear buffer
            self.metrics_buffer[deployment_id] = []
            
            logger.info(f"Flushed {len(metrics_data)} metrics for deployment {deployment_id}")
            
        except Exception as e:
            logger.error(f"Error flushing metrics: {e}")
    
    def create_cost_estimate(self, deployment_metadata: Dict) -> Dict:
        """Estimate monthly costs for a deployment"""
        # Base costs (simplified)
        lambda_requests_per_month = 100000
        lambda_gb_seconds = lambda_requests_per_month * 3  # 3GB memory, 1 sec avg
        
        costs = {
            'lambda_requests': lambda_requests_per_month * 0.0000002,  # $0.20 per 1M requests
            'lambda_compute': lambda_gb_seconds * 0.0000166667,  # $0.0000166667 per GB-second
            'api_gateway': lambda_requests_per_month * 0.0000035,  # $3.50 per 1M requests
            'storage': 0.023 * 0.5,  # $0.023 per GB, assume 500MB
            'data_transfer': 0.09 * 1,  # $0.09 per GB, assume 1GB
        }
        
        costs['total'] = sum(costs.values())
        
        return {
            'estimated_monthly_cost': round(costs['total'], 2),
            'breakdown': {k: round(v, 2) for k, v in costs.items()},
            'assumptions': {
                'requests_per_month': lambda_requests_per_month,
                'average_latency_seconds': 1,
                'model_size_mb': 500,
                'data_transfer_gb': 1
            }
        }