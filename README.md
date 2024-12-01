# AI ETL Framework

A high-performance, real-time AI ETL pipeline framework designed for scalable data processing with integrated monitoring and testing capabilities.

## Features

- **Containerized Architecture**
  - Docker/Kubernetes deployment
  - Microservices-based design
  - Scalable infrastructure

- **Core Services**
  - MinIO for object storage
  - Prometheus for metrics collection
  - Grafana for monitoring and visualization
  - Support for AI services (Groq)

- **Monitoring & Observability**
  - Real-time system metrics
  - Custom ETL pipeline metrics
  - Grafana dashboards
  - Performance monitoring
  - Resource utilization tracking

## Project Structure

```
.
├── .coveragerc                # Configuration for coverage.py
├── .env                        # Environment variables for development
├── .env.sample                 # Sample environment variables template
├── .gitignore                  # Specifies intentionally untracked files to ignore
├── LICENSE                     # Project license information
├── README.md                   # Project documentation and overview
├── deployment                  # Deployment configurations and Docker setups
│   ├── docker-compose.dev.yml  # Docker Compose configuration for development environment
│   ├── docker-compose.prod.yml # Docker Compose configuration for production environment
│   ├── docker-compose.yml      # Base Docker Compose configuration
│   ├── env
│   │   └── .env.dev            # Environment variables specific to development
│   └── images
│       ├── grafana
│       │   ├── Dockerfile       # Dockerfile for Grafana service
│       │   └── config
│       │       ├── dashboards
│       │       │   ├── etl-infrastructure.json # Grafana dashboard configuration for ETL infrastructure
│       │       │   ├── etl-pipeline.json       # Grafana dashboard configuration for ETL pipeline
│       │       │   └── home.json                # Grafana home dashboard configuration
│       │       ├── grafana.ini                 # Main Grafana configuration file
│       │       └── provisioning
│       │           ├── dashboards
│       │           │   └── dashboard.yaml        # Grafana dashboard provisioning configuration
│       │           └── datasources
│       │               └── datasource.yaml       # Grafana datasource provisioning configuration
│       ├── kafka
│       │   ├── Dockerfile       # Dockerfile for Kafka service
│       │   └── config
│       │       ├── server.properties      # Kafka server configuration
│       │       └── zookeeper.properties   # Zookeeper configuration for Kafka
│       ├── minio
│       │   ├── Dockerfile       # Dockerfile for MinIO service
│       │   └── config
│       │       └── minio.json           # MinIO server configuration
│       └── prometheus
│           ├── Dockerfile       # Dockerfile for Prometheus service
│           └── config
│               └── prometheus.yml      # Prometheus server configuration
├── poetry.lock                 # Locked dependencies for Poetry
├── pyproject.toml              # Poetry project configuration and dependencies
├── pytest.ini                  # Pytest configuration settings
├── src                         # Source code for the AI ETL Framework
│   ├── __init__.py             # Initializes the src package
│   └── ai_etl_framework
│       ├── __init__.py         # Initializes the ai_etl_framework package
│       ├── cli
│       │   ├── ___init__.py     # Initializes the CLI module
│       │   ├── commands
│       │   │   ├── ___init__.py # Initializes the commands submodule
│       │   │   ├── __init__.py  # Initializes the commands submodule
│       │   │   └── test_load.py  # CLI command for testing load operations
│       │   └── main.py          # Entry point for the CLI interface
│       ├── common
│       │   └── __init__.py      # Initializes the common utilities module
│       ├── config
│       │   ├── __init__.py      # Initializes the config module
│       │   └── settings.py      # Configuration settings for the framework
│       └── load_testing
│           ├── __init__.py      # Initializes the load_testing module
│           └── system_tester.py # Scripts and tools for system testing
└── tests                        # Test suites for the AI ETL Framework
    ├── __init__.py             # Initializes the tests package
    ├── conftest.py             # Pytest fixtures and configurations
    ├── test_config
    │   ├── __init__.py         # Initializes the test_config module
    │   └── test_settings.py    # Tests for configuration settings
    ├── test_pipeline
    │   └── __init__.py         # Initializes the test_pipeline module
    └── test_services
        └── __init__.py         # Initializes the test_services module

```
## Load test
```bash
poetry run locust
```
## Quick Start

1. **Install Dependencies**
   ```bash
   poetry install
   ```

2. **Start Infrastructure Services**
   ```bash
   
# Start all services with build
docker-compose -f deployment/docker-compose.yml up --build

# Start all services in detached mode
docker-compose -f deployment/docker-compose.yml up --build -d

# Stop all running services
docker-compose -f deployment/docker-compose.yml stop

# Stop all services and remove containers, networks, and volumes
docker-compose -f deployment/docker-compose.yml down

# View real-time logs for all services
docker-compose -f deployment/docker-compose.yml logs -f

# View real-time logs for a specific service (e.g., extractor)
docker-compose -f deployment/docker-compose.yml logs -f extractor

# Rebuild and restart a specific service (e.g., extractor)
docker-compose -f deployment/docker-compose.yml up --build extractor

# Check the status and health of all services
docker ps

# Execute a command inside a running service container (e.g., extractor)
docker exec -it <container_name> bash

# Remove all unused Docker resources
docker system prune -af

# Inspect details about a specific container
docker inspect <container_name>

# Monitor resource usage for running containers
docker stats

# Build Docker images without starting services
docker-compose -f deployment/docker-compose.yml build

# Start only Prometheus and Grafana
docker-compose -f deployment/docker-compose.yml up --build prometheus grafana

   ```

1. **Access Services**
   - MinIO Console: http://localhost:9001 (login: minioadmin/minioadmin)
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (login: admin/admin)

## CLI Commands

The framework provides a command-line interface for various operations:

1. **Load Testing**
   ```bash
   # Run load test with default settings
   poetry run ai-etl test-load

   # Run with custom parameters
   poetry run ai-etl test-load \
     --duration 10 \
     --cpu-intensity 80 \
     --memory-size 1000 \
     --file-size 100 \
     --interval 2
   ```

   Options:
   - `--duration`: Test duration in minutes
   - `--cpu-intensity`: CPU load percentage (1-100)
   - `--memory-size`: Memory allocation in MB
   - `--file-size`: Size of test files to upload
   - `--interval`: Interval between operations

## Testing

### Unit Tests
```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_config/test_settings.py

# Run tests in parallel
poetry run pytest -n auto
```

### Coverage Reports
```bash
# Generate coverage report
poetry run pytest
# View HTML report in coverage_html/index.html
```

## Monitoring

### Grafana Dashboards

The framework includes pre-configured Grafana dashboards for:
- System Resource Monitoring
  - CPU Usage
  - Memory Utilization
  - Disk I/O
  - Network Traffic
- MinIO Storage Metrics
- ETL Pipeline Performance

### Metrics Collection

- System Metrics:
  - CPU utilization per core
  - Memory usage and allocation
  - Disk usage and I/O operations
  - Network throughput
- Storage Metrics:
  - MinIO bucket statistics
  - Object count and size
  - Storage capacity and usage
- Pipeline Metrics:
  - Processing rates
  - Error rates
  - Latency measurements

## Configuration

### Environment Variables
Create a `.env` file in the project root:
```env
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
```

### Service Configurations
Service-specific configurations are located in:
```
deployment/
└── images/
    ├── grafana/config/
    ├── prometheus/config/
    └── minio/config/
```

## Development

### Adding New Components

1. Create a new module in the appropriate directory
2. Add unit tests in the `tests` directory
3. Update the documentation
4. Run tests to ensure everything works

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure coverage
5. Submit a pull request

## License

[MIT License](LICENSE)