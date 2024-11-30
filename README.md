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
ai_etl_framework/
├── src/
│   ├── ai_etl_framework/
│   │   ├── config/            # Configuration management
│   │   ├── core/             # Core functionality
│   │   ├── services/         # External service integrations
│   │   ├── pipeline/         # Pipeline components
│   │   │   ├── extractors/
│   │   │   ├── transformers/
│   │   │   └── loaders/
│   │   └── utils/
├── tests/
├── deployment/
│   ├── docker-compose.yml
│   └── images/
│       ├── grafana/
│       ├── prometheus/
│       └── minio/
└── examples/
```

## Quick Start

1. **Install Dependencies**
   ```bash
   poetry install
   ```

2. **Start Infrastructure Services**
   ```bash
   cd deployment
   docker-compose up -d
   ```

3. **Access Services**
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