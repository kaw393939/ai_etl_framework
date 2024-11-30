import click
import logging
import sys

from ai_etl_framework.load_testing.system_tester import ETLSystemTester


@click.command()
@click.option('--duration', '-d', default=5, help='Test duration in minutes')
@click.option('--minio-endpoint', default='localhost:9000', help='MinIO endpoint')
@click.option('--minio-access-key', default='minioadmin', help='MinIO access key')
@click.option('--minio-secret-key', default='minioadmin', help='MinIO secret key')
@click.option('--bucket-name', default='test-bucket', help='MinIO bucket name')
@click.option('--log-level', default='INFO', 
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Logging level')
@click.option('--cpu-intensity', default=50, 
              type=click.IntRange(1, 100),
              help='CPU load intensity (1-100)')
@click.option('--memory-size', default=100,
              help='Memory allocation size in MB')
@click.option('--file-size', default=1,
              help='Size of test files to upload (MB)')
@click.option('--interval', default=5,
              help='Interval between operations in seconds')
def test_load(duration, minio_endpoint, minio_access_key, 
              minio_secret_key, bucket_name, log_level,
              cpu_intensity, memory_size, file_size, interval):
    """Run system load tests for monitoring.
    
    This command will generate load on:
    - CPU through intensive calculations
    - Memory by allocating and deallocating memory
    - Storage through MinIO operations
    - Network through data transfer
    """
    # Configure logging
    log_level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR
    }
    
    logging.basicConfig(
        level=log_level_map[log_level],
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger('load_test')
    
    try:
        click.echo("Initializing ETL System Load Tester...")
        tester = ETLSystemTester(
            minio_endpoint=minio_endpoint,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
            bucket_name=bucket_name,
            log_level=log_level_map[log_level]
        )
        
        click.echo(f"""
Load Test Configuration:
- Duration: {duration} minutes
- CPU Intensity: {cpu_intensity}%
- Memory Size: {memory_size}MB
- File Size: {file_size}MB
- Operation Interval: {interval}s
        """)
        
        click.echo("Starting load test...")
        tester.run_test_cycle(
            duration_minutes=duration,
            cpu_intensity=cpu_intensity,
            memory_size=memory_size,
            file_size=file_size,
            interval=interval
        )
        
    except KeyboardInterrupt:
        click.echo("\nTest interrupted by user. Cleaning up...")
        logger.info("Test stopped by user")
    except Exception as e:
        click.echo(f"\nError during test: {str(e)}", err=True)
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        click.echo("Load test completed.")