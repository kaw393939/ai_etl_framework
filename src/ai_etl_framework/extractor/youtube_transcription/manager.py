# youtube_transcription/manager.py

from __future__ import annotations
import threading
import queue
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from ai_etl_framework.extractor.models.tasks import TranscriptionTask, TaskStatus
from ai_etl_framework.common.logger import setup_logger
from ai_etl_framework.extractor.youtube_transcription.downloader import VideoDownloader
from ai_etl_framework.extractor.youtube_transcription.splitter import AudioSplitter
from ai_etl_framework.extractor.youtube_transcription.audio_transcriber import AudioTranscriber
from ai_etl_framework.config.settings import config

logger = setup_logger(__name__)

class TranscriptionManager:
    """
    Manages tasks by handling downloading, splitting, and transcribing.
    Utilizes worker threads to process tasks concurrently with async support.
    """

    def __init__(self):
        """Initialize the TranscriptionManager with workers and a task queue."""
        self.tasks: List[TranscriptionTask] = []
        self.task_queue = queue.Queue(maxsize=config.worker.max_queue_size)
        self.shutdown_event = threading.Event()
        self.workers: List[threading.Thread] = []
        self.lock = threading.Lock()
        self.workers_started = False
        self.executor = ThreadPoolExecutor(max_workers=config.worker.max_workers)

        # Initialize components
        self.downloader = VideoDownloader()
        self.splitter = AudioSplitter()
        self.transcriber = AudioTranscriber()

        self._start_workers()

    def _start_workers(self):
        """Start worker threads if they haven't been started yet."""
        with self.lock:
            if self.workers_started:
                logger.warning("Worker threads have already been started. Skipping.")
                return

            for i in range(config.worker.max_workers):
                worker = threading.Thread(target=self._worker, name=f"Worker-{i+1}", daemon=False)
                worker.start()
                self.workers.append(worker)
                logger.info(f"Started worker thread: {worker.name}")

            self.workers_started = True

    def add_task(self, url: str) -> bool:
        """Add a new task to the queue."""
        with self.lock:
            if any(task.url == url for task in self.tasks):
                logger.warning(f"Task for URL {url} already exists.")
                return False

            task = TranscriptionTask(url=url)
            self.tasks.append(task)
            logger.info(f"Task {task.id} added for URL: {url}")

        try:
            self.task_queue.put(task, block=False)
            logger.info(f"Task {task.id} queued successfully.")
            return True
        except queue.Full:
            logger.warning(f"Task queue is full. Could not add task for URL: {url}")
            with self.lock:
                self.tasks.remove(task)
            return False

    async def _process_task_async(self, task: TranscriptionTask):
        """Process a task asynchronously."""
        try:
            logger.info(f"Task {task.id}: Starting processing for URL: {task.url}")
            task.update_status(TaskStatus.DOWNLOADING)

            # Download the video
            success, error = await self.downloader.download_video(task)
            if not success:
                task.set_error(error or "Failed to download video")
                task.update_status(TaskStatus.FAILED)
                logger.error(f"Task {task.id}: Failed to download video - {error}")
                return

            logger.info(f"Task {task.id}: Download complete for video: {task.title}")

            # Split the audio
            task.update_status(TaskStatus.SPLITTING)
            chunks_info = await self.splitter.split_audio(task)

            if not chunks_info:
                task.set_error("Audio splitting failed")
                task.update_status(TaskStatus.FAILED)
                logger.error(f"Task {task.id}: Audio splitting failed")
                return

            logger.info(f"Task {task.id}: Audio split into {len(chunks_info)} chunks")

            # Transcribe the audio chunks
            task.update_status(TaskStatus.TRANSCRIBING)
            transcription_success = await self.transcriber.transcribe_all_chunks(task)

            if not transcription_success:
                task.set_error("Audio youtube_transcription failed")
                task.update_status(TaskStatus.FAILED)
                logger.error(f"Task {task.id}: Audio youtube_transcription failed")
                return

            logger.info(f"Task {task.id}: Audio youtube_transcription completed")

            # Merge the transcripts
            merge_success = await self.transcriber.merge_transcripts(task)

            if not merge_success:
                task.set_error("Merging transcripts failed")
                task.update_status(TaskStatus.FAILED)
                logger.error(f"Task {task.id}: Merging transcripts failed")
                return

            logger.info(f"Task {task.id}: Transcripts merged successfully")

            task.update_status(TaskStatus.COMPLETED)
            logger.info(f"Task {task.id}: Task completed successfully")

        except Exception as e:
            error_msg = f"Error processing Task {task.id}: {str(e)}"
            logger.exception(error_msg)
            task.set_error(error_msg)
            task.update_status(TaskStatus.FAILED)

    def _worker(self):
        """Worker thread to process tasks using an event loop."""
        while not self.shutdown_event.is_set():
            try:
                task: TranscriptionTask = self.task_queue.get(timeout=1)
                logger.info(f"{threading.current_thread().name} picked up Task {task.id}")

                try:
                    # Create a new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    # Run the async task processing
                    loop.run_until_complete(self._process_task_async(task))
                    loop.close()

                except Exception as e:
                    logger.exception(f"Unexpected error processing Task {task.id}: {e}")
                    task.set_error(str(e))
                    task.update_status(TaskStatus.FAILED)
                finally:
                    self.task_queue.task_done()
                    logger.info(f"{threading.current_thread().name} completed Task {task.id}")

            except queue.Empty:
                continue
            except Exception as e:
                logger.exception(f"Unexpected error in worker thread: {e}")

    def resume_task(self, task: TranscriptionTask):
        """Resume a paused or failed task."""
        with self.lock:
            if task.can_resume():
                task.update_status(TaskStatus.PENDING)
                self.task_queue.put(task)
                logger.info(f"Task {task.id} has been resumed.")
            else:
                logger.warning(f"Task {task.id} is not in a resumable state.")

    def shutdown(self):
        """Shutdown the TranscriptionManager, ensuring all workers exit cleanly."""
        logger.info("TranscriptionManager: Initiating shutdown...")
        self.shutdown_event.set()

        # Wait for all tasks in the queue to be processed
        self.task_queue.join()
        logger.debug("TranscriptionManager: All tasks in the queue have been processed.")

        # Terminate worker threads
        for worker in self.workers:
            worker.join(timeout=2)
            if worker.is_alive():
                logger.warning(f"{worker.name} did not terminate properly.")
            else:
                logger.info(f"{worker.name} terminated successfully.")

        # Shutdown the thread pool executor
        self.executor.shutdown(wait=True)
        logger.info("TranscriptionManager: Thread pool executor has been shut down.")

    def get_tasks(self) -> List[TranscriptionTask]:
        """Get the list of tasks."""
        with self.lock:
            return list(self.tasks)

    def get_task_by_id(self, task_id: str) -> Optional[TranscriptionTask]:
        """Retrieve a task by its ID."""
        with self.lock:
            for task in self.tasks:
                if task.id == task_id:
                    return task
        return None