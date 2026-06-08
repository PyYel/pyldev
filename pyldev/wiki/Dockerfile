# ==========================================
# STAGE 1: The Builder
# ==========================================
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN pip install --no-cache-dir wheel
RUN pip wheel --wheel-dir=/build/wheels \
    mkdocs \
    mkdocs-material \
    mkdocs-to-pdf

# ==========================================
# STAGE 2: The Final Runtime Environment
# ==========================================
FROM python:3.11-slim

# Install system layout engines AND Chromium for headless JS/Mermaid rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Fix: Create a symlink so calls to "chromium-browser" redirect to the actual "chromium" binary
RUN ln -s /usr/bin/chromium /usr/bin/chromium-browser

WORKDIR /app

COPY --from=builder /build/wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/* && rm -rf /wheels

# This shell script handles the clean compilation and copy loop
ENTRYPOINT ["sh", "-c", "mkdir -p /workspace && cp -R /docs/* /workspace/ && cd /workspace && mkdocs build && cp /workspace/site/pdf/document.pdf /output/document.pdf"]