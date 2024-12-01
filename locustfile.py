from locust import HttpUser, TaskSet, task, between
import random
import string
import json

class ExtractorTasks(TaskSet):
    def on_start(self):
        """Executed when a simulated user starts."""
        pass  # Can be used for setup if needed

    @task(2)
    def process_url_normal(self):
        """Normal processing without stress."""
        sample_urls = [
            "http://example.com",
            "http://example.org",
            "http://example.net",
            "http://test.com",
            "http://localhost:8000",  # Adjust if using Docker networking
        ]
        url = random.choice(sample_urls)
        headers = {'Content-Type': 'application/json'}
        payload = {"url": url}
        with self.client.post("/process-url/", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Failed to process URL: {url}")
            else:
                response.success()

    @task(3)
    def process_url_memory_stress(self):
        """Processing with memory stress."""
        sample_urls = [
            "http://example.com",
            "http://example.org",
            "http://example.net",
            "http://test.com",
            "http://localhost:8000",
        ]
        url = random.choice(sample_urls)
        headers = {'Content-Type': 'application/json'}
        
        # Randomize memory size between 100MB and 500MB
        memory_size_mb = random.randint(100, 500)
        payload = {
            "url": url,
            "stress_memory": True,
            "memory_size_mb": memory_size_mb,
            "stress_disk": False,
            "stress_cpu": False
        }
        with self.client.post("/process-url/", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Memory stress failed for URL: {url}")
            else:
                response.success()

    @task(2)
    def process_url_disk_stress(self):
        """Processing with disk stress."""
        sample_urls = [
            "http://example.com",
            "http://example.org",
            "http://example.net",
            "http://test.com",
            "http://localhost:8000",
        ]
        url = random.choice(sample_urls)
        headers = {'Content-Type': 'application/json'}
        
        # Randomize disk size between 100MB and 500MB
        disk_size_mb = random.randint(100, 500)
        payload = {
            "url": url,
            "stress_memory": False,
            "stress_disk": True,
            "disk_size_mb": disk_size_mb,
            "stress_cpu": False
        }
        with self.client.post("/process-url/", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Disk stress failed for URL: {url}")
            else:
                response.success()

    @task(1)
    def process_url_both_stress(self):
        """Processing with both memory and disk stress."""
        sample_urls = [
            "http://example.com",
            "http://example.org",
            "http://example.net",
            "http://test.com",
            "http://localhost:8000",
        ]
        url = random.choice(sample_urls)
        headers = {'Content-Type': 'application/json'}
        
        # Randomize memory and disk sizes between 100MB and 300MB
        memory_size_mb = random.randint(100, 300)
        disk_size_mb = random.randint(100, 300)
        payload = {
            "url": url,
            "stress_memory": True,
            "memory_size_mb": memory_size_mb,
            "stress_disk": True,
            "disk_size_mb": disk_size_mb,
            "stress_cpu": False
        }
        with self.client.post("/process-url/", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Both memory and disk stress failed for URL: {url}")
            else:
                response.success()

    @task(1)
    def process_url_cpu_stress(self):
        """Processing with CPU stress."""
        sample_urls = [
            "http://example.com",
            "http://example.org",
            "http://example.net",
            "http://test.com",
            "http://localhost:8000",
        ]
        url = random.choice(sample_urls)
        headers = {'Content-Type': 'application/json'}
        
        # Randomize CPU load between 10% and 90%
        cpu_load_percent = random.randint(10, 90)
        # Randomize CPU stress duration between 5 and 30 seconds
        cpu_duration_sec = random.randint(5, 30)
        payload = {
            "url": url,
            "stress_memory": False,
            "memory_size_mb": 0,
            "stress_disk": False,
            "disk_size_mb": 0,
            "stress_cpu": True,
            "cpu_load_percent": cpu_load_percent,
            "cpu_duration_sec": cpu_duration_sec
        }
        with self.client.post("/process-url/", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"CPU stress failed for URL: {url}")
            else:
                response.success()

    @task(1)
    def process_url_all_stress(self):
        """Processing with memory, disk, and CPU stress."""
        sample_urls = [
            "http://example.com",
            "http://example.org",
            "http://example.net",
            "http://test.com",
            "http://localhost:8000",
        ]
        url = random.choice(sample_urls)
        headers = {'Content-Type': 'application/json'}
        
        # Randomize parameters
        memory_size_mb = random.randint(50, 300)
        disk_size_mb = random.randint(50, 300)
        cpu_load_percent = random.randint(10, 90)
        cpu_duration_sec = random.randint(5, 30)
        
        payload = {
            "url": url,
            "stress_memory": True,
            "memory_size_mb": memory_size_mb,
            "stress_disk": True,
            "disk_size_mb": disk_size_mb,
            "stress_cpu": True,
            "cpu_load_percent": cpu_load_percent,
            "cpu_duration_sec": cpu_duration_sec
        }
        with self.client.post("/process-url/", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"All stress operations failed for URL: {url}")
            else:
                response.success()

class ExtractorUser(HttpUser):
    tasks = [ExtractorTasks]
    wait_time = between(1, 3)  # Wait between 1 and 3 seconds between tasks
