from storage.base_manager import AbstractFileManager
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from typing import List, Optional
import logging

# load environment variables
import os
from dotenv import load_dotenv
from botocore.config import Config

load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
ENDPOINT_URL = os.getenv("SCAYLE_S3_ENDPOINT")
# for testing with localstack
ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT", ENDPOINT_URL)

AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")


class S3FileManager(AbstractFileManager):
    """SCAYLE S3-based implementation of file manager"""

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: Optional[str] = ENDPOINT_URL,
        aws_access_key_id: Optional[str] = AWS_ACCESS_KEY_ID,
        aws_secret_access_key: Optional[str] = AWS_SECRET_ACCESS_KEY,
        region_name: Optional[str] = AWS_REGION,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(logger)
        self.bucket_name = bucket_name
        # Build client parameters dict
        client_params ={
            "aws_access_key_id": aws_access_key_id,
            "aws_secret_access_key": aws_secret_access_key,
            "config": Config(s3={"addressing_style": "path"}),
        }
        if region_name:
            client_params["region_name"] = region_name
        if endpoint_url:
            client_params["endpoint_url"] = endpoint_url

        self.s3 = boto3.client("s3", **client_params)
        exists_bucket = self.verify_bucket()
        if not exists_bucket:
            self.logger.warning(
                f"Bucket {self.bucket_name} does not exist or is not accessible."
            )
            self.logger.info(f"Creating bucket: {self.bucket_name}")
            try:
                self.create_bucket(bucket_name=self.bucket_name)
                self.logger.info(f"Bucket {self.bucket_name} created successfully.")
            except Exception as e:
                self.logger.error(f"Error creating bucket {self.bucket_name}: {e}")
                self.bucket_name = None
        else:
            self.logger.info(f"Using existing bucket: {self.bucket_name}")

    # Verify bucket exists
    def verify_bucket(self, bucket_name: Optional[str] = None) -> bool:
        bucket_name = bucket_name or self.bucket_name
        try:
            self.s3.head_bucket(Bucket=bucket_name)
            self.logger.info(f"Bucket {bucket_name} exists and is accessible.")
            return True
        except ClientError as e:
            try:
                error_code = int(e.response["Error"]["Code"])
                if error_code == 404:
                    self.logger.error(f"Bucket {bucket_name} does not exist.")
                else:
                    self.logger.error(f"Error accessing bucket {bucket_name}: {e}")
                return False
            except ValueError:
                error_code = e.response["Error"]["Code"]
                if error_code == "NoSuchBucket":
                    self.logger.error(f"Bucket {bucket_name} does not exist.")
                elif error_code == "AccessDenied":
                    self.logger.error(f"Access denied to bucket {bucket_name}.")
                else:
                    self.logger.error(f"Unexpected error accessing bucket {bucket_name}: {e}")
                return False

    # Create bucket
    def create_bucket(self, bucket_name: Optional[str] = None, aws_region: Optional[str] = None, set_bucket: bool = True):
        if bucket_name:
            try:
                if aws_region:
                    self.s3.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={"LocationConstraint": aws_region},
                    )
                else:
                    self.s3.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration=(
                            {"LocationConstraint": self.s3._client_config.region_name}
                            if self.s3._client_config.region_name
                            else {}
                        ),
                    )
                self.logger.info(f"Bucket {bucket_name} created successfully.")
            except ClientError as e:
                self.logger.error(f"Error creating bucket {bucket_name}: {e}")
            if set_bucket:
                self.bucket_name = bucket_name
                self.logger.info(f"Bucket set to {bucket_name}")
        else:
            self.logger.error("Bucket name must be provided to create a bucket.")

    # List buckets
    def list_buckets(self) -> List[str]:
        try:
            response = self.s3.list_buckets()
            buckets = [bucket["Name"] for bucket in response.get("Buckets", [])]
            self.logger.info(f"Buckets: {buckets}")
            return buckets
        except ClientError as e:
            self.logger.error(f"Error listing buckets: {e}")
            return []

    # Set bucket
    def set_bucket(self, bucket_name: str):
        try:
            exist_bucket = self.verify_bucket(bucket_name)
            if not exist_bucket:
                self.logger.warning(
                    f"Bucket {bucket_name} does not exist or is not accessible."
                )
                self.logger.info(f"Creating bucket: {bucket_name}")
                self.create_bucket(bucket_name)
                self.logger.info(f"Bucket set to {bucket_name}")
            else:
                self.bucket_name = bucket_name
                self.logger.info(f"Bucket set to {bucket_name}")
        except Exception as e:
            self.logger.error(f"Error setting bucket {bucket_name}: {e}")

    def get_bucket(self) -> Optional[str]:
        return self.bucket_name

    def upload_file(self, local_path: str, remote_path: str):
        try:
            self.s3.upload_file(local_path, self.bucket_name, remote_path)
            self.logger.info(
                f"File {local_path} uploaded to {remote_path} in bucket {self.bucket_name}."
            )
        except FileNotFoundError:
            self.logger.error(f"The file {local_path} was not found.")
        except NoCredentialsError:
            self.logger.error("Credentials not available.")
        except ClientError as e:
            self.logger.error(
                f"Error uploading file {local_path} to {remote_path}: {e}"
            )

    def delete_file(self, remote_path: str):
        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=remote_path)
            self.logger.info(
                f"File {remote_path} deleted from bucket {self.bucket_name}."
            )
        except ClientError as e:
            self.logger.error(f"Error deleting file {remote_path}: {e}")

    def download_file(self, remote_path: str, local_path: str):
        try:
            self.s3.download_file(self.bucket_name, remote_path, local_path)
            self.logger.info(f"File {remote_path} downloaded to {local_path}.")
        except ClientError as e:
            self.logger.error(f"Error downloading file {remote_path}: {e}")

    def list_files(self, prefix: str = "", page_size=1000) -> List[str]:
        MAX_PAGE_SIZE = 1000
        page_size = min(page_size, MAX_PAGE_SIZE)
        try:
            # using paginator
            paginator = self.s3.get_paginator("list_objects_v2")
            files = []
            page_number = 0
            self.logger.info(f"Listing files with prefix '{prefix}' in bucket '{self.bucket_name}'...")
            # Iterate through each page of results
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                # Extract 'key' from each object in the page
                page_number += 1
                page_files = [item["Key"] for item in page.get("Contents", [])]
                files.extend(page_files)
                # logging each page's files
                self.logger.info(
                    f"Page {page_number} in bucket {self.bucket_name} with prefix '{prefix}': {page_files}"
                )
            self.logger.info(
                f"Total files in bucket {self.bucket_name} with prefix '{prefix}' across {page_number} page(s): {len(files)} files"
                )
            return files

        except ClientError as e:
            self.logger.error(f"Error listing files with prefix '{prefix}': {e}")
            return []

    def create_directory(self, path: str):
        if not path.endswith("/"):
            path += "/"
        try:
            self.s3.put_object(Bucket=self.bucket_name, Key=path)
            self.logger.info(f"Directory {path} created in bucket {self.bucket_name}.")
        except ClientError as e:
            self.logger.error(f"Error creating directory {path}: {e}")

    def delete_directory(self, path: str):
        if not path.endswith("/"):
            path += "/"
        try:
            # List all objects with the given prefix (directory path)
            response = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=path)
            objects_to_delete = [
                {"Key": obj["Key"]} for obj in response.get("Contents", [])
            ]
            if objects_to_delete:
                self.s3.delete_objects(
                    Bucket=self.bucket_name, Delete={"Objects": objects_to_delete}
                )
                self.logger.info(
                    f"Directory {path} and its contents deleted from bucket {self.bucket_name}."
                )
            else:
                self.logger.info(f"No objects found in directory {path} to delete.")
        except ClientError as e:
            self.logger.error(f"Error deleting directory {path}: {e}")

    def delete_bucket(self, bucket_name: str):
        """
        Delete the specified bucket. The bucket MUST NOT be the current working bucket.
        """
        try:
            # check if the bucket is the current one
            if self.bucket_name == bucket_name:
                self.logger.warning(
                    f"Deleting current working bucket {bucket_name} is not allowed. Please set another bucket using set_bucket({{another_bucket_name}}) first!"
                )
                return
            else:
                self.s3.delete_bucket(Bucket=bucket_name)
                self.logger.info(f"Bucket {bucket_name} deleted successfully.")
        except ClientError as e:
            self.logger.error(f"Error deleting bucket {bucket_name}: {e}")

"""
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bucket_name = S3_BUCKET_NAME or "datagems.zhaw.s3.demo"
    s3_manager = S3FileManager(bucket_name, region_name=AWS_REGION)
    if not s3_manager.verify_bucket():
        s3_manager.create_bucket(bucket_name)
    s3_manager.list_buckets()
    # Example usage
    s3_manager.set_bucket("datagems.zhaw.s3.another-bucket-name")
    s3_manager.upload_file('README.MD', 'remote_README.MD')
    s3_manager.download_file('remote_README.MD', 'downloaded_README.MD')
    s3_manager.list_files()
    s3_manager.delete_file('remote_README.MD')
    s3_manager.list_files()
    s3_manager.create_directory('new_folder/')
    s3_manager.list_files()
    s3_manager.delete_directory('new_folder/')
    s3_manager.list_files()
    s3_manager.delete_bucket("datagems.zhaw.s3.another-bucket-name")
    s3_manager.set_bucket("datagems.zhaw.s3.demo")
    s3_manager.delete_bucket("datagems.zhaw.s3.another-bucket-name")
"""
