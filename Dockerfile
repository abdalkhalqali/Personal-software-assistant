FROM python:3.13-slim AS root

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    curl \
    unzip \
    git \
    git-lfs \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install

# Install Node.js 20 for building the React frontend
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Bun for frontend builds
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:${PATH}"

# Copy dependency files
COPY frontend/package.json frontend/bun.lock* /app/frontend/
COPY requirements.txt requirements_web_demo.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir \
    torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements_web_demo.txt && \
    pip install --no-cache-dir fastapi uvicorn spaces

# Install and build frontend
COPY frontend/ /app/frontend/
RUN cd /app/frontend && \
    bun install && \
    bun run build

# Copy the rest of the project
COPY . /app/

# Clean up frontend source to save space, keep only dist/
RUN rm -rf /app/frontend/src /app/frontend/node_modules

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# Run the API server
ENV PYTHONUNBUFFERED=1
CMD ["python", "api_server.py"]
