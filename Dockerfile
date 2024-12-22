# Dockerfile

FROM python:3.9-slim-buster

# Install system dependencies if needed
RUN apt-get update && apt-get install -y ffmpeg wget curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements.txt
COPY requirements.txt /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your main script
COPY extract_recipe.py /app

# Default command is bash. Override with your own at runtime if needed.
CMD [ "/bin/bash" ]
