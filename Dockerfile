# Dockerfile

FROM python:3.9-slim-buster

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    wget \
    curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY extract_recipe.py .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the FastAPI server
CMD ["python", "extract_recipe.py"]