import logging
from datetime import datetime

from locust import HttpUser, TaskSet, task, between
import random
import string
import json
import sseclient

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




logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('transcription_tests.log'),
        logging.StreamHandler()
    ]
)


class TranscriptionTasks(TaskSet):
    def on_start(self):
        """Executed when a simulated user starts."""
        self.logger = logging.getLogger(__name__)
        self.sample_videos = [
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=_Z5-P9v3F8w",
        ]

    @task(1)
    def process_transcription(self):
        """Test the transcription streaming endpoint with comprehensive logging."""
        url = random.choice(self.sample_videos)
        start_time = datetime.now()

        self.logger.info(f"Starting transcription request for URL: {url}")
        headers = {'Content-Type': 'application/json'}
        payload = {"url": url}

        with self.client.post("/tasks/", json=payload, headers=headers, stream=True, catch_response=True) as response:
            if response.status_code != 200:
                error_msg = f"Failed to initiate transcription. Status code: {response.status_code}"
                self.logger.error(error_msg)
                response.failure(error_msg)
                return

            try:
                client = sseclient.SSEClient(response)
                saw_completion = False
                event_count = 0

                for event in client.events():
                    event_count += 1
                    current_time = datetime.now()
                    elapsed_time = (current_time - start_time).total_seconds()

                    if not event.data:
                        self.logger.warning(f"[{elapsed_time:.2f}s] Empty event received")
                        continue

                    # Log the complete event data
                    self.logger.info(f"[{elapsed_time:.2f}s] Stream event {event_count}: {event.data}")

                    try:
                        data = json.loads(event.data)
                        if data.get('status') == "Completed":
                            saw_completion = True
                            duration = (current_time - start_time).total_seconds()
                            self.logger.info(f"Task completed successfully in {duration:.2f} seconds")
                            response.success()
                            return
                        elif data.get('error'):
                            self.logger.error(f"Task failed with error: {data['error']}")
                            response.failure(data['error'])
                            return

                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse event data: {str(e)}")
                        continue

                # Handle stream completion
                if not saw_completion:
                    if event_count > 0:
                        self.logger.warning(f"Stream ended after {event_count} events without explicit completion")
                        response.success()  # Consider it successful if we received events
                    else:
                        self.logger.error("Stream ended without receiving any events")
                        response.failure("No events received")

            except Exception as e:
                self.logger.error(f"Stream processing error: {str(e)}", exc_info=True)
                response.failure(f"Stream processing error: {str(e)}")


class TranscriptionUser(HttpUser):
    tasks = [TranscriptionTasks]
    wait_time = between(5, 15)

    def on_start(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("New transcription user started")