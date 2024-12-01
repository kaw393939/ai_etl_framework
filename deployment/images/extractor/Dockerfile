# Use an official Python runtime as a base image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy only the necessary files for Poetry to install dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-dev

# Copy the entire source directory
COPY src /app/src

# Copy the .env file
COPY .env /app/.env

# Set PYTHONPATH to the src directory
ENV PYTHONPATH=/app/src

# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run the FastAPI app
CMD ["poetry", "run", "uvicorn", "ai_etl_framework.extractor.app:app", "--host", "0.0.0.0", "--port", "8000"]
