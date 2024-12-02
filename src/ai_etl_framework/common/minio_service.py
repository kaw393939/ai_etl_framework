# storage/minio_service.py
import time
from typing import Optional, BinaryIO, Dict
import io
import json
from datetime import datetime
import os

from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile
from urllib3 import PoolManager

from ai_etl_framework.config.settings import config
from ai_etl_framework.common.logger import setup_logger

logger = setup_logger(__name__)


class MinioStorageService:
    """Handles all storage operations using MinIO as the backend."""

    def __init__(self):
        """Initialize MinIO client with configuration settings."""
        self.client = Minio(
            endpoint=config.minio.endpoint,
            access_key=config.minio.access_key,
            secret_key=config.minio.secret_key,
            secure=config.minio.secure,
            http_client=PoolManager(timeout=30)  # Add timeout configuration
        )
        self.bucket_name = config.minio.bucket
        self.ensure_bucket_exists()

    def ensure_bucket_exists(self):
        """Create the default bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise

    def _get_object_path(self, task_id: str, file_type: str, filename: str) -> str:
        """Generate a consistent object path for MinIO storage."""
        return f"{task_id}/{file_type}/{filename}"

    async def save_file(self, task_id: str, file_type: str, file: BinaryIO,
                        filename: str, metadata: Optional[Dict] = None) -> str:
        """Save a file to MinIO storage with improved error handling."""
        try:
            object_path = self._get_object_path(task_id, file_type, filename)

            # If file is UploadFile, read its content
            if isinstance(file, UploadFile):
                content = await file.read()
                file_obj = io.BytesIO(content)
            else:
                file_obj = file

            # Ensure we're at the start of the file
            file_obj.seek(0)

            # Get file size
            file_obj.seek(0, 2)  # Seek to end
            file_size = file_obj.tell()
            file_obj.seek(0)  # Reset to start

            # Extract content_type from metadata if provided
            if metadata is None:
                metadata = {}
            content_type = metadata.pop('Content-Type', None) or metadata.pop('content-type', None) or 'application/octet-stream'

            # Upload to MinIO with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.client.put_object(
                        bucket_name=self.bucket_name,
                        object_name=object_path,
                        data=file_obj,
                        length=file_size,
                        content_type=content_type,  # Pass content_type here
                        metadata=metadata  # metadata should not include Content-Type
                    )
                    logger.info(f"Saved file to MinIO: {object_path}")
                    return object_path
                except S3Error as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed, retrying: {str(e)}")
                        file_obj.seek(0)  # Reset file position for retry
                        time.sleep(1)  # Add delay between retries
                    else:
                        raise

        except Exception as e:
            logger.error(f"Error saving file to MinIO: {e}")
            raise

    async def get_file(self, task_id: str, file_type: str, filename: str) -> Optional[io.BytesIO]:
        """Retrieve a file from MinIO storage."""
        try:
            object_path = self._get_object_path(task_id, file_type, filename)
            response = self.client.get_object(self.bucket_name, object_path)

            # Read the entire object into memory
            data = response.read()
            return io.BytesIO(data)

        except Exception as e:
            logger.error(f"Error retrieving file from MinIO: {e}")
            return None

    async def save_json(self, task_id: str, file_type: str, filename: str, data: Dict) -> str:
        """Save JSON data to MinIO storage."""
        try:
            json_str = json.dumps(data, indent=2)
            json_bytes = json_str.encode('utf-8')

            object_path = self._get_object_path(task_id, file_type, filename)

            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_path,
                data=io.BytesIO(json_bytes),
                length=len(json_bytes),
                content_type='application/json',  # Set content_type here
                metadata={}  # Empty or user-defined metadata only
            )

            logger.info(f"Saved JSON to MinIO: {object_path}")
            return object_path

        except Exception as e:
            logger.error(f"Error saving JSON to MinIO: {e}")
            raise

    async def get_json(self, task_id: str, file_type: str, filename: str) -> Optional[Dict]:
        """Retrieve JSON data from MinIO storage."""
        try:
            object_path = self._get_object_path(task_id, file_type, filename)
            response = self.client.get_object(self.bucket_name, object_path)

            # Read and parse JSON data
            json_str = response.read().decode('utf-8')
            return json.loads(json_str)

        except Exception as e:
            logger.error(f"Error retrieving JSON from MinIO: {e}")
            return None

    async def list_files(self, task_id: str, file_type: Optional[str] = None) -> list:
        """List all files for a task, optionally filtered by file type."""
        try:
            prefix = f"{task_id}"
            if file_type:
                prefix = f"{prefix}/{file_type}"

            objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]

        except Exception as e:
            logger.error(f"Error listing files from MinIO: {e}")
            return []

    async def delete_file(self, task_id: str, file_type: str, filename: str) -> bool:
        """Delete a file from MinIO storage."""
        try:
            object_path = self._get_object_path(task_id, file_type, filename)
            self.client.remove_object(self.bucket_name, object_path)
            logger.info(f"Deleted file from MinIO: {object_path}")
            return True

        except Exception as e:
            logger.error(f"Error deleting file from MinIO: {e}")
            return False

    async def get_temporary_url(self, task_id: str, file_type: str, filename: str,
                                expires: int = 3600) -> Optional[str]:
        """Generate a temporary URL for file access."""
        try:
            object_path = self._get_object_path(task_id, file_type, filename)
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_path,
                expires=expires
            )
            return url

        except Exception as e:
            logger.error(f"Error generating temporary URL: {e}")
            return None
