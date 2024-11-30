from pathlib import Path
import time
import random
import multiprocessing
import psutil
import numpy as np
from minio import Minio
from datetime import datetime
import logging
from typing import Optional, Dict, Any
import math
from io import BytesIO

class ETLSystemTester:
    """System load tester for ETL framework monitoring"""

    def __init__(
        self,
        minio_endpoint: str = "localhost:9000",
        access_key: str = "minioadmin",
        secret_key: str = "minioadmin",
        bucket_name: str = "test-bucket",
        log_level: int = logging.INFO,
    ):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.minio_client = Minio(
            minio_endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )
        self.bucket_name = bucket_name
        self.ensure_bucket_exists()
        self.cpu_count = multiprocessing.cpu_count()

    def ensure_bucket_exists(self) -> None:
        """Ensure the test bucket exists"""
        try:
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
                self.logger.info(f"Created bucket: {self.bucket_name}")
        except Exception as e:
            self.logger.error(f"Error creating bucket: {e}")
            raise

    def generate_test_data(self, size_mb: int = 1) -> bytes:
        """Generate random test data of specified size"""
        return np.random.bytes(size_mb * 1024 * 1024)

    def cpu_intensive_task(self):
        """CPU intensive calculation"""
        matrix_size = 100
        # Matrix multiplication is CPU intensive
        matrix_a = np.random.rand(matrix_size, matrix_size)
        matrix_b = np.random.rand(matrix_size, matrix_size)
        return np.dot(matrix_a, matrix_b)

    def cpu_load_simulation(self, intensity: int = 50, duration: int = 10) -> None:
        """
        Simulate CPU load with specified intensity and duration
        
        Args:
            intensity: CPU load percentage (1-100)
            duration: Duration in seconds
        """
        self.logger.info(f"Starting CPU load simulation at {intensity}% for {duration}s")
        
        # Calculate number of CPU cores to use based on intensity
        cores_to_use = max(1, int((intensity / 100.0) * self.cpu_count))
        processes = []
        
        try:
            # Start multiple processes for CPU load
            for _ in range(cores_to_use):
                p = multiprocessing.Process(target=self._cpu_worker, args=(duration,))
                p.start()
                processes.append(p)

            # Wait for all processes to complete
            for p in processes:
                p.join()
                
        except Exception as e:
            self.logger.error(f"Error in CPU simulation: {e}")

    def _cpu_worker(self, duration: int):
        """Worker process for CPU load"""
        end_time = time.time() + duration
        while time.time() < end_time:
            self.cpu_intensive_task()

    def memory_load_simulation(self, size_mb: int = 100, duration: int = 5) -> None:
        """Simulate memory usage of specified size"""
        self.logger.info(f"Allocating {size_mb}MB of memory for {duration}s")
        try:
            # Create multiple arrays to fragment memory
            chunk_size = 10  # MB per chunk
            num_chunks = size_mb // chunk_size
            data_chunks = []
            
            for i in range(num_chunks):
                # Allocate memory in chunks and perform operations
                chunk = np.random.rand(chunk_size * 256, 512)  # ~10MB per chunk
                # Perform some operations to ensure memory is actually used
                chunk = np.sqrt(chunk) * np.log(np.abs(chunk) + 1)
                data_chunks.append(chunk)
                
            time.sleep(duration)
            
            # Explicitly delete the chunks
            for chunk in data_chunks:
                del chunk
            data_chunks.clear()
            
        except Exception as e:
            self.logger.error(f"Error in memory simulation: {e}")


    def write_to_minio(self, data_size_mb: int = 1) -> Optional[str]:
        """Write test data to MinIO with multiple chunks"""
        try:
            # Split the upload into multiple chunks for more network activity
            chunk_size = min(data_size_mb, 5)  # 5MB chunks
            num_chunks = max(1, data_size_mb // chunk_size)
            
            for i in range(num_chunks):
                # Generate data and wrap it in BytesIO
                data = self.generate_test_data(chunk_size)
                data_stream = BytesIO(data)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                object_name = f"test_data_{timestamp}_chunk_{i}.bin"
                
                self.minio_client.put_object(
                    self.bucket_name,
                    object_name,
                    data_stream,
                    len(data)
                )
                self.logger.info(f"Written chunk {i+1}/{num_chunks} ({chunk_size}MB) to MinIO: {object_name}")
            
            return object_name
        except Exception as e:
            self.logger.error(f"Error writing to MinIO: {e}")
            return None

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net = psutil.net_io_counters()
            
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': memory.percent,
                'memory_used': memory.used,
                'memory_total': memory.total,
                'disk_percent': disk.percent,
                'disk_used': disk.used,
                'disk_total': disk.total,
                'network': {
                    'bytes_sent': net.bytes_sent,
                    'bytes_recv': net.bytes_recv,
                    'packets_sent': net.packets_sent,
                    'packets_recv': net.packets_recv
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting system metrics: {e}")
            return {}

    def run_test_cycle(
        self,
        duration_minutes: int = 5,
        cpu_intensity: int = 50,
        memory_size: int = 100,
        file_size: int = 1,
        interval: int = 5
    ) -> None:
        """Run a complete test cycle with specified parameters"""
        self.logger.info(
            f"Starting test cycle for {duration_minutes} minutes with "
            f"CPU: {cpu_intensity}%, Memory: {memory_size}MB, "
            f"File Size: {file_size}MB, Interval: {interval}s"
        )
        
        end_time = time.time() + (duration_minutes * 60)
        start_metrics = self.get_system_metrics()

        while time.time() < end_time:
            try:
                # Run CPU and memory tests concurrently
                cpu_process = multiprocessing.Process(
                    target=self.cpu_load_simulation,
                    args=(cpu_intensity, interval)
                )
                mem_process = multiprocessing.Process(
                    target=self.memory_load_simulation,
                    args=(memory_size, interval)
                )
                
                cpu_process.start()
                mem_process.start()

                # Write data to MinIO while CPU and memory are being stressed
                self.write_to_minio(file_size)

                cpu_process.join()
                mem_process.join()

                # Log detailed metrics
                current_metrics = self.get_system_metrics()
                if current_metrics:
                    self.logger.info(
                        f"System Metrics:\n"
                        f"CPU: {current_metrics['cpu_percent']}%\n"
                        f"Memory: {current_metrics['memory_percent']}% "
                        f"({current_metrics['memory_used'] / (1024**3):.2f}GB / "
                        f"{current_metrics['memory_total'] / (1024**3):.2f}GB)\n"
                        f"Disk: {current_metrics['disk_percent']}%\n"
                        f"Network: Sent {current_metrics['network']['bytes_sent'] / (1024**2):.2f}MB, "
                        f"Received {current_metrics['network']['bytes_recv'] / (1024**2):.2f}MB"
                    )

                # Small sleep to prevent overwhelming the system
                time.sleep(max(0, interval - 2))

            except Exception as e:
                self.logger.error(f"Error in test cycle: {e}")
                continue

        # Log test summary
        end_metrics = self.get_system_metrics()
        if start_metrics and end_metrics:
            total_network_sent = (end_metrics['network']['bytes_sent'] - 
                                start_metrics['network']['bytes_sent']) / (1024**2)
            total_network_recv = (end_metrics['network']['bytes_recv'] - 
                                start_metrics['network']['bytes_recv']) / (1024**2)
            
            self.logger.info(
                f"\nTest Summary:\n"
                f"Total Network Traffic: Sent {total_network_sent:.2f}MB, "
                f"Received {total_network_recv:.2f}MB"
            )