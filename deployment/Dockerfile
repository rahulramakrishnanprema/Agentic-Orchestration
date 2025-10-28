# Multi-stage Dockerfile for Aristotle-I Platform
# This Dockerfile builds both the Python backend and React frontend

# ============================================================================
# Stage 1: Build React Frontend
# ============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY Agentic_UI/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source and config files
COPY Agentic_UI/src ./src
COPY Agentic_UI/.env.* ./
COPY Agentic_UI/*.config.* ./
COPY Agentic_UI/*.config.ts ./
COPY Agentic_UI/*.json ./
COPY Agentic_UI/*.js ./
COPY Agentic_UI/index.html ./

# Build frontend
RUN npm run build

# ============================================================================
# Stage 2: Build Python Backend
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Copy backend source code
COPY main.py .
COPY config/ ./config/
COPY core/ ./core/
COPY agents/ ./agents/
COPY graph/ ./graph/
COPY services/ ./services/
COPY tools/ ./tools/
COPY workflows/ ./workflows/
COPY ui/ ./ui/
COPY prompts/ ./prompts/
COPY standards/ ./standards/

# Copy built frontend to be served
COPY --from=frontend-builder /app/frontend/dist ./static

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${UI_PORT:-8080}/api/health || exit 1

# Expose ports
# UI_PORT: HTTP server for React frontend and Python backend (default 8080)
# REACT_DEV_PORT: React development server (default 5173, not used in production)
EXPOSE 8080 5173

# Create non-root user for security
RUN useradd -m -u 1000 aristotlei && chown -R aristotlei:aristotlei /app
USER aristotlei

# Default command - starts the main application
CMD ["python", "main.py"]

