"""
AWS Lambda Integration Tests
"""
import pytest
import boto3
import json
import base64
from moto import mock_lambda, mock_iam, mock_ecr
from datetime import datetime


@mock_lambda
@mock_iam
@mock_ecr
class TestLambdaIntegration:
    """Test Lambda integration"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup Lambda resources"""
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.iam_client = boto3.client('iam', region_name='us-east-1')
        self.ecr_client = boto3.client('ecr', region_name='us-east-1')
        
        # Create IAM role for Lambda
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        self.iam_client.create_role(
            RoleName='serveml-lambda-role',
            AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        
        # Create ECR repository
        self.ecr_client.create_repository(repositoryName='serveml-models')
    
    def test_create_lambda_function(self):
        """Test creating Lambda function from container"""
        function_name = 'serveml-test-model'
        
        # Create Lambda function
        response = self.lambda_client.create_function(
            FunctionName=function_name,
            Role='arn:aws:iam::123456789012:role/serveml-lambda-role',
            Code={
                'ImageUri': '123456789012.dkr.ecr.us-east-1.amazonaws.com/serveml-models:latest'
            },
            PackageType='Image',
            MemorySize=2048,
            Timeout=300,
            Environment={
                'Variables': {
                    'MODEL_PATH': '/var/task/model.pkl',
                    'FRAMEWORK': 'sklearn'
                }
            },
            Tags={
                'deployment-id': 'test-deployment',
                'user-id': 'test-user',
                'framework': 'sklearn'
            }
        )
        
        assert response['FunctionName'] == function_name
        assert response['MemorySize'] == 2048
        assert response['Timeout'] == 300
    
    def test_invoke_lambda_function(self):
        """Test invoking Lambda function"""
        function_name = 'serveml-test-model'
        
        # Mock function exists
        self.lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.9',
            Role='arn:aws:iam::123456789012:role/serveml-lambda-role',
            Handler='lambda_function.handler',
            Code={'ZipFile': b'fake code'}
        )
        
        # Test payload
        test_payload = {
            "data": [5.1, 3.5, 1.4, 0.2]
        }
        
        # Invoke function
        response = self.lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            LogType='Tail',
            Payload=json.dumps(test_payload)
        )
        
        assert response['StatusCode'] == 200
    
    def test_lambda_concurrency_settings(self):
        """Test Lambda concurrency configuration"""
        function_name = 'serveml-test-model'
        
        # Create function
        self.lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.9',
            Role='arn:aws:iam::123456789012:role/serveml-lambda-role',
            Handler='lambda_function.handler',
            Code={'ZipFile': b'fake code'}
        )
        
        # Set reserved concurrent executions
        response = self.lambda_client.put_function_concurrency(
            FunctionName=function_name,
            ReservedConcurrentExecutions=10
        )
        
        assert response['ReservedConcurrentExecutions'] == 10
    
    def test_lambda_provisioned_concurrency(self):
        """Test provisioned concurrency for low latency"""
        function_name = 'serveml-test-model'
        
        # Create function
        self.lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.9',
            Role='arn:aws:iam::123456789012:role/serveml-lambda-role',
            Handler='lambda_function.handler',
            Code={'ZipFile': b'fake code'}
        )
        
        # Create alias
        self.lambda_client.create_alias(
            FunctionName=function_name,
            Name='production',
            FunctionVersion='$LATEST'
        )
        
        # Set provisioned concurrency
        response = self.lambda_client.put_provisioned_concurrency_config(
            FunctionName=function_name,
            Qualifier='production',
            ProvisionedConcurrentExecutions=5
        )
        
        assert response['ProvisionedConcurrentExecutions'] == 5
    
    def test_lambda_environment_variables(self):
        """Test Lambda environment variable configuration"""
        function_name = 'serveml-test-model'
        
        env_vars = {
            'MODEL_PATH': '/var/task/model.pkl',
            'FRAMEWORK': 'sklearn',
            'MAX_BATCH_SIZE': '32',
            'LOG_LEVEL': 'INFO'
        }
        
        # Create function with env vars
        response = self.lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.9',
            Role='arn:aws:iam::123456789012:role/serveml-lambda-role',
            Handler='lambda_function.handler',
            Code={'ZipFile': b'fake code'},
            Environment={'Variables': env_vars}
        )
        
        assert response['Environment']['Variables'] == env_vars
    
    def test_lambda_memory_configurations(self):
        """Test different memory configurations"""
        memory_configs = [512, 1024, 2048, 3008, 10240]  # Up to 10GB
        
        for memory in memory_configs:
            function_name = f'serveml-test-{memory}mb'
            
            response = self.lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role='arn:aws:iam::123456789012:role/serveml-lambda-role',
                Handler='lambda_function.handler',
                Code={'ZipFile': b'fake code'},
                MemorySize=memory
            )
            
            assert response['MemorySize'] == memory
    
    def test_lambda_timeout_configurations(self):
        """Test timeout configurations"""
        timeout_configs = [30, 60, 180, 300, 900]  # Up to 15 minutes
        
        for timeout in timeout_configs:
            function_name = f'serveml-test-{timeout}s'
            
            response = self.lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role='arn:aws:iam::123456789012:role/serveml-lambda-role',
                Handler='lambda_function.handler',
                Code={'ZipFile': b'fake code'},
                Timeout=timeout
            )
            
            assert response['Timeout'] == timeout
    
    def test_lambda_error_handling(self):
        """Test Lambda error handling and dead letter queue"""
        function_name = 'serveml-test-model'
        
        # Create function
        self.lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.9',
            Role='arn:aws:iam::123456789012:role/serveml-lambda-role',
            Handler='lambda_function.handler',
            Code={'ZipFile': b'fake code'}
        )
        
        # Configure dead letter queue
        dlq_config = {
            'TargetArn': 'arn:aws:sqs:us-east-1:123456789012:serveml-dlq'
        }
        
        response = self.lambda_client.put_function_configuration(
            FunctionName=function_name,
            DeadLetterConfig=dlq_config
        )
        
        assert 'DeadLetterConfig' in response
    
    def test_lambda_x_ray_tracing(self):
        """Test X-Ray tracing configuration"""
        function_name = 'serveml-test-model'
        
        # Create function with X-Ray tracing
        response = self.lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.9',
            Role='arn:aws:iam::123456789012:role/serveml-lambda-role',
            Handler='lambda_function.handler',
            Code={'ZipFile': b'fake code'},
            TracingConfig={'Mode': 'Active'}
        )
        
        assert response['TracingConfig']['Mode'] == 'Active'
    
    def test_lambda_vpc_configuration(self):
        """Test Lambda VPC configuration for security"""
        function_name = 'serveml-test-model'
        
        vpc_config = {
            'SubnetIds': ['subnet-12345', 'subnet-67890'],
            'SecurityGroupIds': ['sg-12345']
        }
        
        # Create function in VPC
        response = self.lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.9',
            Role='arn:aws:iam::123456789012:role/serveml-lambda-role',
            Handler='lambda_function.handler',
            Code={'ZipFile': b'fake code'},
            VpcConfig=vpc_config
        )
        
        assert response['VpcConfig']['SubnetIds'] == vpc_config['SubnetIds']
        assert response['VpcConfig']['SecurityGroupIds'] == vpc_config['SecurityGroupIds']