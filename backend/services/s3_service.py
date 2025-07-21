"""
S3 Service for handling file uploads and downloads
"""
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Tuple, Optional
import os
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class S3Service:
    """Handle S3 operations for ServeML"""
    
    def __init__(self, bucket_name: str = None, region: str = 'us-east-1'):
        self.s3_client = boto3.client('s3', region_name=region)
        self.bucket_name = bucket_name or os.environ.get('S3_BUCKET', 'serveml-uploads')
        
    def generate_presigned_upload_url(
        self, 
        deployment_id: str, 
        filename: str,
        expiration: int = 3600
    ) -> Dict[str, str]:
        """
        Generate presigned URL for direct S3 upload
        
        Returns:
            Dict with 'url' and 'fields' for form data
        """
        try:
            key = f"deployments/{deployment_id}/{filename}"
            
            # Generate presigned POST URL
            response = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=key,
                ExpiresIn=expiration,
                Conditions=[
                    ["content-length-range", 0, 524288000],  # Max 500MB
                ]
            )
            
            logger.info(f"Generated presigned URL for: {key}")
            return response
            
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise
    
    def generate_presigned_download_url(
        self,
        key: str,
        expiration: int = 3600
    ) -> str:
        """Generate presigned URL for downloading a file"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating download URL: {e}")
            raise
    
    def upload_file(self, file_path: str, key: str) -> bool:
        """Upload a file to S3"""
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, key)
            logger.info(f"Uploaded {file_path} to s3://{self.bucket_name}/{key}")
            return True
        except ClientError as e:
            logger.error(f"Error uploading file: {e}")
            return False
    
    def upload_deployment_trigger(
        self,
        deployment_id: str,
        metadata: Dict
    ) -> bool:
        """
        Upload trigger file to initiate deployment
        This file triggers the S3 event Lambda
        """
        try:
            trigger_key = f"deployments/{deployment_id}/trigger.json"
            trigger_data = {
                "deployment_id": deployment_id,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata
            }
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=trigger_key,
                Body=json.dumps(trigger_data),
                ContentType='application/json'
            )
            
            logger.info(f"Uploaded trigger file: {trigger_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error uploading trigger: {e}")
            return False
    
    def check_files_exist(self, deployment_id: str) -> Tuple[bool, bool]:
        """Check if model and requirements files exist"""
        model_exists = False
        requirements_exists = False
        
        try:
            # Check model file
            model_key = f"deployments/{deployment_id}/model.pkl"
            self.s3_client.head_object(Bucket=self.bucket_name, Key=model_key)
            model_exists = True
        except ClientError:
            pass
        
        try:
            # Check requirements file
            req_key = f"deployments/{deployment_id}/requirements.txt"
            self.s3_client.head_object(Bucket=self.bucket_name, Key=req_key)
            requirements_exists = True
        except ClientError:
            pass
        
        return model_exists, requirements_exists
    
    def delete_deployment_files(self, deployment_id: str) -> bool:
        """Delete all files for a deployment"""
        try:
            prefix = f"deployments/{deployment_id}/"
            
            # List all objects with prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                logger.warning(f"No files found for deployment: {deployment_id}")
                return True
            
            # Delete all objects
            objects = [{'Key': obj['Key']} for obj in response['Contents']]
            
            self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': objects}
            )
            
            logger.info(f"Deleted {len(objects)} files for deployment: {deployment_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting deployment files: {e}")
            return False
    
    def get_deployment_size(self, deployment_id: str) -> int:
        """Get total size of deployment files in bytes"""
        try:
            prefix = f"deployments/{deployment_id}/"
            total_size = 0
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_size += obj['Size']
            
            return total_size
            
        except ClientError as e:
            logger.error(f"Error calculating deployment size: {e}")
            return 0
    
    def create_bucket_if_not_exists(self) -> bool:
        """Create S3 bucket if it doesn't exist"""
        try:
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} already exists")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Create bucket
                try:
                    if self.s3_client.meta.region_name == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={
                                'LocationConstraint': self.s3_client.meta.region_name
                            }
                        )
                    
                    # Enable versioning
                    self.s3_client.put_bucket_versioning(
                        Bucket=self.bucket_name,
                        VersioningConfiguration={'Status': 'Enabled'}
                    )
                    
                    logger.info(f"Created bucket: {self.bucket_name}")
                    return True
                except ClientError as create_error:
                    logger.error(f"Error creating bucket: {create_error}")
                    return False
            else:
                logger.error(f"Error checking bucket: {e}")
                return False