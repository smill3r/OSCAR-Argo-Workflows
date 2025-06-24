FROM python:3.9-slim

WORKDIR /app

# Install system dependencies first
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script
COPY sentiment-analysis.py .

# Set the entrypoint
CMD ["python", "sentiment-analysis.py"]