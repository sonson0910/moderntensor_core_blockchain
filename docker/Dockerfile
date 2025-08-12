# ModernTensor Core - Production Docker Image
# Multi-stage build for optimized production deployment

# ========================================
# Stage 1: Build Environment
# ========================================
FROM node:18.19.0-alpine3.19 AS node-builder

# Security updates
RUN apk update && apk upgrade && apk add --no-cache dumb-init

WORKDIR /app/smartcontract

# Copy package files
COPY moderntensor_aptos/mt_core/smartcontract/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy smart contract sources
COPY moderntensor_aptos/mt_core/smartcontract/ ./

# Compile smart contracts
RUN npm run compile

# ========================================
# Stage 2: Python Build Environment
# ========================================
FROM python:3.11.7-slim-bookworm AS python-builder

WORKDIR /app

# Security updates and system dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    build-essential \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY moderntensor_aptos/requirements*.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY moderntensor_aptos/ ./moderntensor_aptos/

# Install ModernTensor Core
RUN pip install -e ./moderntensor_aptos/

# ========================================
# Stage 3: Production Runtime
# ========================================
FROM python:3.11.7-slim-bookworm AS production

# Set environment variables
ENV PYTHONPATH="/app:$PYTHONPATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production
ENV MODERNTENSOR_ENV=production

# Create app user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Install runtime dependencies with security updates
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Install Node.js (needed for smart contract operations)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get update && apt-get install -y nodejs=18.19.0* \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=python-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=python-builder /app/moderntensor_aptos ./moderntensor_aptos
COPY --from=node-builder /app/smartcontract ./moderntensor_aptos/mt_core/smartcontract

# Copy additional files
COPY moderntensor_aptos/security ./security
COPY moderntensor_aptos/performance ./performance
COPY moderntensor_aptos/monitoring ./monitoring

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/config /app/monitoring/results \
    && chown -R appuser:appuser /app

# Copy configuration files
COPY moderntensor_aptos/mt_core/config/*.yaml ./moderntensor_aptos/mt_core/config/

# Health check script
COPY --chown=appuser:appuser <<EOF /app/healthcheck.py
#!/usr/bin/env python3
import sys
import asyncio
from moderntensor_aptos.mt_core.async_client import CoreAsyncClient
from moderntensor_aptos.mt_core.config.config_loader import get_config

async def health_check():
    try:
        config = get_config()
        client = CoreAsyncClient()
        await client.connect()
        
        # Test basic operations
        test_address = "0x" + "1" * 40
        await client.get_balance(test_address)
        await client.disconnect()
        
        print("✅ Health check passed")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(health_check())
    sys.exit(0 if result else 1)
EOF

RUN chmod +x /app/healthcheck.py

# Switch to app user
USER appuser

# Expose ports
EXPOSE 8000 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python /app/healthcheck.py

# Default command
CMD ["python", "-m", "moderntensor_aptos.mt_core.network.app.main"]

# ========================================
# Labels for metadata
# ========================================
LABEL maintainer="ModernTensor Team"
LABEL version="1.0.0"
LABEL description="ModernTensor Core - Decentralized AI Training Platform"
LABEL org.opencontainers.image.source="https://github.com/moderntensor/core"
LABEL org.opencontainers.image.documentation="https://docs.moderntensor.io"
LABEL org.opencontainers.image.vendor="ModernTensor"
LABEL org.opencontainers.image.licenses="MIT" 