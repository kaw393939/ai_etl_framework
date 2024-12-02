# Use an official Python runtime as a base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy only the necessary files for Poetry to install dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy the entire source directory
COPY src /app/src

# Set PYTHONPATH to the src directory
ENV PYTHONPATH=/app/src

# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run the FastAPI app
CMD ["poetry", "run", "uvicorn", "ai_etl_framework.extractor.app:app", "--host", "0.0.0.0", "--port", "8000"]