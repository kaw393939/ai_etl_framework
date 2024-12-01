Sure! Below is the enhanced and carefully rewritten version of your `README.md` file. This version removes references to Kubernetes, ensures Docker commands are clear and well-formatted, clarifies headings, and adds additional information to provide a comprehensive overview of the project.

---

# **AI ETL Framework**

A high-performance, real-time AI ETL pipeline framework designed for scalable data processing with integrated monitoring, testing, and observability capabilities.

---

## **Features**

### **Containerized Architecture**
- **Docker Deployment**: Easily deploy and manage services using Docker.
- **Microservices-Based Design**: Modular architecture allowing independent scaling and maintenance.
- **Scalable Infrastructure**: Designed to handle increasing data loads with minimal effort.

### **Core Services**
- **MinIO**: High-performance, S3-compatible object storage.
- **Prometheus**: Robust metrics collection and alerting system.
- **Grafana**: Comprehensive monitoring and visualization dashboards.
- **AI Integration**: Integration with Groq for advanced AI processing.

### **Monitoring & Observability**
- **Real-Time Metrics**: Immediate visibility into system performance.
- **Custom ETL Metrics**: Track specific metrics tailored to ETL pipeline performance.
- **Pre-configured Dashboards**: Ready-to-use Grafana dashboards for quick insights.
- **Performance Monitoring**: Monitor CPU, memory, disk I/O, and network traffic.
- **Resource Utilization Tracking**: Keep an eye on system resource usage to ensure optimal performance.

---

## **Project Structure**

```plaintext
.
├── .coveragerc                # Coverage configuration
├── .env                       # Environment variables for development
├── .env.sample                # Template for environment variables
├── .gitignore                 # Ignored files
├── LICENSE                    # License information
├── README.md                  # Project documentation
├── deployment                 # Deployment configurations
│   ├── docker-compose.yml      # Main Docker Compose configuration
│   ├── docker-compose.dev.yml  # Development environment configuration
│   ├── docker-compose.prod.yml # Production environment configuration
│   ├── env                     # Environment-specific configurations
│   │   └── .env.dev            # Development environment variables
│   └── images
│       ├── grafana             # Grafana configurations and Dockerfile
│       ├── kafka               # Kafka configurations and Dockerfile
│       ├── minio               # MinIO configurations and Dockerfile
│       └── prometheus          # Prometheus configurations and Dockerfile
├── pyproject.toml             # Poetry project configuration
├── poetry.lock                # Locked dependencies for Poetry
├── pytest.ini                 # Pytest settings
├── src                        # Source code
│   ├── ai_etl_framework        # Main framework code
│   └── tests                   # Unit and integration tests
└── tests                      # Test cases
```

---

## **Quick Start**

### **1. Install Dependencies**
Ensure you have [Poetry](https://python-poetry.org/) installed. Then, install the project dependencies:
```bash
poetry install
```

### **2. Start Infrastructure Services**
Use Docker Compose to build and run all necessary services.

#### **Basic Setup:**
Start all services with build:
```bash
docker-compose -f deployment/docker-compose.yml up --build
```

#### **Detached Mode:**
Start all services in the background:
```bash
docker-compose -f deployment/docker-compose.yml up --build -d
```

#### **Stop Services:**
Stop all running services:
```bash
docker-compose -f deployment/docker-compose.yml stop
```

#### **Clean Up:**
Stop all services and remove containers, networks, and volumes:
```bash
docker-compose -f deployment/docker-compose.yml down
```

#### **View Real-Time Logs:**
View logs for all services:
```bash
docker-compose -f deployment/docker-compose.yml logs -f
```

View logs for a specific service (e.g., extractor):
```bash
docker-compose -f deployment/docker-compose.yml logs -f extractor
```

#### **Rebuild and Restart a Specific Service:**
Rebuild and restart a specific service (e.g., extractor):
```bash
docker-compose -f deployment/docker-compose.yml up --build extractor
```

#### **Check Service Status:**
Check the status and health of all running services:
```bash
docker ps
```

#### **Execute Commands Inside a Container:**
Execute a command inside a running service container (e.g., extractor):
```bash
docker exec -it <container_name> bash
```

#### **Remove Unused Docker Resources:**
Remove all unused Docker resources:
```bash
docker system prune -af
```

#### **Inspect a Specific Container:**
Inspect details about a specific container:
```bash
docker inspect <container_name>
```

#### **Monitor Resource Usage:**
Monitor resource usage for running containers:
```bash
docker stats
```

#### **Build Docker Images Without Starting Services:**
Build Docker images without starting the services:
```bash
docker-compose -f deployment/docker-compose.yml build
```

#### **Start Specific Services:**
Start only Prometheus and Grafana:
```bash
docker-compose -f deployment/docker-compose.yml up --build prometheus grafana
```

### **3. Access Services**
- **MinIO Console**: [http://localhost:9001](http://localhost:9001)  
  - **Username**: `minioadmin`  
  - **Password**: `minioadmin`
- **Prometheus**: [http://localhost:9090](http://localhost:9090)
- **Grafana**: [http://localhost:3000](http://localhost:3000)  
  - **Username**: `admin`  
  - **Password**: `admin`

---

## **CLI Commands**

The framework provides a command-line interface for various operations.

### **Load Testing**

Run load tests with default settings:
```bash
poetry run ai-etl test-load
```

Run load tests with custom parameters:
```bash
poetry run ai-etl test-load --duration 10 --cpu-intensity 80 --memory-size 1000 --file-size 100 --interval 2
```

#### **Options:**
| Option              | Description                          |
|---------------------|--------------------------------------|
| `--duration`        | Test duration in minutes            |
| `--cpu-intensity`   | CPU load percentage (1-100)         |
| `--memory-size`     | Memory allocation in MB             |
| `--file-size`       | Size of test files to upload (MB)    |
| `--interval`        | Interval between operations (seconds)|

---

## **Testing**

### **Run All Tests**
Execute all unit and integration tests:
```bash
poetry run pytest
```

### **Run Specific Tests**
Run tests from a specific test file:
```bash
poetry run pytest tests/test_config/test_settings.py
```

### **Run Tests in Parallel**
Run tests in parallel to speed up execution:
```bash
poetry run pytest -n auto
```

### **Generate Coverage Reports**
Generate and view code coverage reports:
```bash
# Generate coverage report
poetry run pytest --cov

# View the HTML coverage report
open coverage_html/index.html
```

---

## **Monitoring**

### **Grafana Dashboards**
Pre-configured Grafana dashboards include:
- **System Metrics**: CPU Usage, Memory Utilization, Disk I/O, Network Traffic
- **MinIO Metrics**: Storage Capacity, Object Count
- **ETL Pipeline Metrics**: Processing Rates, Error Rates, Latency Measurements

### **Metrics Collection**
- **System Metrics**:
  - CPU usage per core
  - Memory usage and allocation
  - Disk usage and I/O operations
  - Network throughput
- **Storage Metrics**:
  - MinIO bucket statistics
  - Object count and size
  - Storage capacity and usage
- **Pipeline Metrics**:
  - Processing performance
  - Error tracking
  - Task durations

---

## **Configuration**

### **Environment Variables**
Create a `.env` file in the project root to configure environment variables:
```env
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
```

### **Service Configurations**
Service-specific configurations are located in:
```plaintext
deployment/
└── images/
    ├── grafana/config/
    ├── prometheus/config/
    └── minio/config/
```

- **Grafana**:
  - Dashboard and datasource configurations
- **Prometheus**:
  - Metrics collection and scraping configurations
- **MinIO**:
  - Storage configurations

---

## **Development**

### **Adding New Features**
1. **Add New Modules**:
   - Create a new module in the `src/ai_etl_framework/` directory.
2. **Write Tests**:
   - Add corresponding unit and integration tests under the `tests/` directory.
3. **Update Documentation**:
   - Document new features or changes in the `README.md` file.
4. **Verify Changes**:
   - Run tests to ensure new features work as expected:
     ```bash
     poetry run pytest
     ```

### **Contribution Workflow**
1. **Fork the Repository**: Create your own fork of the repository.
2. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/new-feature
   ```
3. **Make Your Changes**: Implement your feature or fix.
4. **Run Tests**: Ensure all tests pass.
   ```bash
   poetry run pytest
   ```
5. **Submit a Pull Request**: Push your changes and open

---

## **License**

This project is licensed under the [MIT License](LICENSE).

---

## **Additional Information**

### **Load Testing with Locust**
The framework includes load testing capabilities using Locust to ensure system reliability under various loads.

#### **Run Load Tests**
```bash
poetry run locust
```
- Access the Locust web interface at [http://localhost:8089](http://localhost:8089)
- Configure your load test parameters and start testing.

### **Grafana Provisioning**
Grafana is pre-configured with datasources and dashboards to provide immediate insights into system performance and ETL pipeline metrics.

#### **Datasource Configuration**
Ensure Prometheus is set as the default datasource in Grafana:
- **URL**: `http://prometheus:9090`
- **Access**: `proxy`
- **Default**: `true`

#### **Dashboard Configuration**
Dashboards are automatically provisioned from the `deployment/images/grafana/config/provisioning/dashboards/` directory.

### **Prometheus Configuration**
Prometheus is configured to scrape metrics from all core services. Ensure that all services expose their metrics endpoints correctly.

#### **Scrape Configuration Example**
```yaml
scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
        labels:
          environment: 'production'

  - job_name: 'minio'
    metrics_path: /minio/v2/metrics/cluster
    scheme: http
    static_configs:
      - targets: ['minio:9000']
        labels:
          service: 'minio'
    tls_config:
      insecure_skip_verify: true
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'minio-cluster'

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
        labels:
          role: 'node_exporter'
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'node-exporter'

  - job_name: 'grafana'
    static_configs:
      - targets: ['grafana:3000']
        labels:
          service: 'grafana'
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'grafana_dashboard'

  - job_name: 'extractor'
    metrics_path: /metrics
    static_configs:
      - targets: ['extractor:8000']
        labels:
          service: 'extractor_service'
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'extractor_service'
```

---

This enhanced `README.md` now provides a clear, structured, and comprehensive guide to your AI ETL Framework. It ensures that all Docker commands are well-formatted and easy to follow, removes unnecessary references to Kubernetes, and includes additional sections for load testing and Grafana provisioning to give users a complete understanding of the project.

Feel free to further customize it based on any additional specific requirements or details of your project!