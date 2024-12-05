# Use the main application Dockerfile as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    python3-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install ALL dependencies including dev dependencies for testing
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy source code and tests
COPY src /app/src
COPY tests /app/tests

# Set PYTHONPATH
ENV PYTHONPATH=/app/src

# Default command runs pytest
CMD ["poetry", "run", "pytest", "/app/tests", "-v", "-s"]