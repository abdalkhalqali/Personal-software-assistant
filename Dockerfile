FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for building the React frontend
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Bun
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:${PATH}"

# Copy dependency files first for better caching
COPY requirements_web_demo.txt .
COPY requirements.txt .
COPY frontend/package.json frontend/bun.lock /app/frontend/

# Install Python dependencies
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir fastapi uvicorn \
    && pip install --no-cache-dir -r requirements_web_demo.txt \
    && pip install --no-cache-dir qwen-vl-utils

# Install frontend dependencies and build
COPY frontend/ /app/frontend/
RUN cd /app/frontend && bun install && bun run build

# Copy the rest of the project
COPY . /app/

# Expose the port Hugging Face expects
EXPOSE 7860

# Run the API server
CMD ["python", "api_server.py"]
