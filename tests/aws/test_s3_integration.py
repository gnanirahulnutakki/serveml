"""
AWS S3 Integration Tests
"""
import pytest
import boto3
import json
import os
from moto import mock_s3
from pathlib import Path


@mock_s3
class TestS3Integration:
    """Test S3 integration"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup S3 resources"""
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.bucket_name = 'serveml-test-models'
        
        # Create bucket
        self.s3_client.create_bucket(Bucket=self.bucket_name)
        
        # Create bucket policy
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{self.bucket_name}/*"
                }
            ]
        }
        self.s3_client.put_bucket_policy(
            Bucket=self.bucket_name,
            Policy=json.dumps(bucket_policy)
        )
    
    def test_model_upload(self):
        """Test uploading model to S3"""
        # Upload model file
        model_data = b"test model data"
        model_key = "models/test-user/test-deployment/model.pkl"
        
        response = self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=model_key,
            Body=model_data,
            ContentType='application/octet-stream',
            Metadata={
                'user-id': 'test-user',
                'deployment-id': 'test-deployment',
                'framework': 'sklearn'
            }
        )
        
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        
        # Verify upload
        obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=model_key)
        assert obj['Body'].read() == model_data
        assert obj['Metadata']['framework'] == 'sklearn'
    
    def test_requirements_upload(self):
        """Test uploading requirements file"""
        requirements = "scikit-learn==1.3.0\nnumpy==1.24.3"
        req_key = "models/test-user/test-deployment/requirements.txt"
        
        response = self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=req_key,
            Body=requirements,
            ContentType='text/plain'
        )
        
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    def test_presigned_url_generation(self):
        """Test generating presigned URLs"""
        model_key = "models/test-user/test-deployment/model.pkl"
        
        # Generate presigned URL for upload
        upload_url = self.s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': model_key
            },
            ExpiresIn=3600
        )
        
        assert upload_url is not None
        assert self.bucket_name in upload_url
        assert model_key in upload_url
        
        # Generate presigned URL for download
        download_url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': model_key
            },
            ExpiresIn=3600
        )
        
        assert download_url is not None
    
    def test_multipart_upload(self):
        """Test multipart upload for large models"""
        # Create large file (50MB)
        large_data = b"0" * (50 * 1024 * 1024)
        model_key = "models/test-user/large-model/model.pkl"
        
        # Initiate multipart upload
        response = self.s3_client.create_multipart_upload(
            Bucket=self.bucket_name,
            Key=model_key
        )
        upload_id = response['UploadId']
        
        # Upload parts (5MB each)
        parts = []
        part_size = 5 * 1024 * 1024
        
        for i in range(0, len(large_data), part_size):
            part_number = (i // part_size) + 1
            part_data = large_data[i:i + part_size]
            
            response = self.s3_client.upload_part(
                Bucket=self.bucket_name,
                Key=model_key,
                PartNumber=part_number,
                UploadId=upload_id,
                Body=part_data
            )
            
            parts.append({
                'ETag': response['ETag'],
                'PartNumber': part_number
            })
        
        # Complete multipart upload
        response = self.s3_client.complete_multipart_upload(
            Bucket=self.bucket_name,
            Key=model_key,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )
        
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    def test_lifecycle_policy(self):
        """Test S3 lifecycle policy for old models"""
        lifecycle_config = {
            'Rules': [
                {
                    'ID': 'Delete old models',
                    'Status': 'Enabled',
                    'Prefix': 'models/',
                    'Transitions': [
                        {
                            'Days': 30,
                            'StorageClass': 'STANDARD_IA'
                        },
                        {
                            'Days': 90,
                            'StorageClass': 'GLACIER'
                        }
                    ],
                    'Expiration': {
                        'Days': 365
                    }
                }
            ]
        }
        
        response = self.s3_client.put_bucket_lifecycle_configuration(
            Bucket=self.bucket_name,
            LifecycleConfiguration=lifecycle_config
        )
        
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    def test_bucket_versioning(self):
        """Test bucket versioning for model updates"""
        # Enable versioning
        response = self.s3_client.put_bucket_versioning(
            Bucket=self.bucket_name,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        
        # Upload multiple versions
        model_key = "models/test-user/versioned-model/model.pkl"
        
        # Version 1
        v1_response = self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=model_key,
            Body=b"model version 1"
        )
        v1_id = v1_response['VersionId']
        
        # Version 2
        v2_response = self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=model_key,
            Body=b"model version 2"
        )
        v2_id = v2_response['VersionId']
        
        # List versions
        versions = self.s3_client.list_object_versions(
            Bucket=self.bucket_name,
            Prefix=model_key
        )
        
        assert len(versions['Versions']) == 2
        assert v1_id != v2_id
    
    def test_bucket_encryption(self):
        """Test bucket encryption"""
        encryption_config = {
            'Rules': [
                {
                    'ApplyServerSideEncryptionByDefault': {
                        'SSEAlgorithm': 'AES256'
                    }
                }
            ]
        }
        
        response = self.s3_client.put_bucket_encryption(
            Bucket=self.bucket_name,
            ServerSideEncryptionConfiguration=encryption_config
        )
        
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        
        # Verify encryption
        encryption = self.s3_client.get_bucket_encryption(Bucket=self.bucket_name)
        assert encryption['ServerSideEncryptionConfiguration']['Rules'][0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm'] == 'AES256'