FROM python:3.11-slim AS root

WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    git \
    git-lfs \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install

# Install Node.js 20 for building frontend
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Bun for frontend builds
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:${PATH}"

# Copy dependency files
COPY frontend/package.json frontend/bun.lock* /app/frontend/
COPY requirements.txt /app/

# Install Python dependencies (optimized for 16GB RAM)
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn

# Install and build frontend
COPY frontend/ /app/frontend/
RUN cd /app/frontend && bun install && bun run build

# Copy the rest of the project
COPY . /app/

# Clean up frontend source to save space
RUN rm -rf /app/frontend/src /app/frontend/node_modules

# Set environment variables for optimal performance
ENV PYTHONUNBUFFERED=1
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
ENV TOKENIZERS_PARALLELISM=false

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/api/health || exit 1

# Run the API server
CMD ["python", "api_server.py"]
