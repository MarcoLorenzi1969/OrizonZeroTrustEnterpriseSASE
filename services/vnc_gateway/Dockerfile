# Orizon Zero Trust Connect - VNC Gateway Dockerfile
# For: Marco @ Syneto/Orizon

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy gateway code
COPY vnc_gateway.py .

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 6080

# Run gateway
CMD ["python", "vnc_gateway.py"]
