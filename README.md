# AI ETL Framework

A high-performance, real-time AI ETL pipeline framework.

## Development Setup

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Run tests:
   ```bash
   poetry run pytest
   ```

3. View coverage report:
   ```bash
   # Coverage report is generated automatically with pytest
   # Open coverage_html/index.html in your browser
   ```

## Running Tests

- Run all tests:
  ```bash
  pytest
  ```

- Run specific test file:
  ```bash
  pytest tests/test_config/test_settings.py
  ```

- Run tests by marker:
  ```bash
  pytest -m "not integration"  # Skip integration tests
  ```

- Run tests in parallel:
  ```bash
  pytest -n auto
  ```

## Coverage

The test suite generates both terminal and HTML coverage reports. The HTML report can be found in `coverage_html/` after running the tests.
