# Use a minimal Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install Docker and dependencies
USER root
RUN apt-get update && \
    apt-get install -y docker.io && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose Flask port
EXPOSE 5050

# Add user jenkins to docker group for Docker usage
RUN groupadd -g 999 docker && \
    usermod -aG docker jenkins

# Run the Flask app
CMD ["python", "devops-assessment-flask-app.py"]
