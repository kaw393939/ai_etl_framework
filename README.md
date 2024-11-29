# AI ETL Framework

A high-performance, real-time AI ETL pipeline framework using Kafka, Qdrant, and Neo4j.

## Features

- Configurable AI service integrations (Groq, OpenAI)
- Vector database support (Weaviate)
- Object storage integration (MinIO)
- Extensible pipeline architecture
- Built-in monitoring and logging
- Docker and Kubernetes support

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai_etl_framework.git
   cd ai_etl_framework
   ```

2. Set up your environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   poetry install
   ```

3. Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run tests:
   ```bash
   pytest
   ```

## Development

### Prerequisites

- Python 3.9+
- Poetry
- Docker (for local development)
- Kubernetes (for deployment)

### Project Structure

```
ai_etl_framework/
├── src/                # Source code
├── tests/              # Test suite
├── examples/           # Usage examples
└── deployment/         # Deployment configurations
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_services/test_groq.py
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

