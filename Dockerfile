# Dockerfile

FROM python:3.9-slim-buster

# Install system dependencies if needed
# e.g., to handle ssl, get ffmpeg, or other packages
RUN apt-get update && apt-get install -y ffmpeg wget curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy your requirements file
COPY requirements.txt /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your script(s)
COPY extract_recipe.py /app

# You may add environment variables if needed, or rely on runtime -e flags
# ENV GEMINI_API_KEY=""

# Default command is bash. You can override it with `docker run ... python extract_recipe.py`
CMD [ "/bin/bash" ]
