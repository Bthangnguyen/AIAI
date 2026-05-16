# Use Python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app



# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies from pre-downloaded wheels (bypass slow Docker network)
COPY wheels/ /tmp/wheels/
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels/ -r requirements.txt \
    && rm -rf /tmp/wheels/

# Copy source code
COPY src/ ./src/
COPY inputs/ ./inputs/

# Create directories for results and cache
RUN mkdir -p /app/results /app/data

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run the application
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
