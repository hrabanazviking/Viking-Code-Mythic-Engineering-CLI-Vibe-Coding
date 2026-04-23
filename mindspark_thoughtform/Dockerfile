# MindSpark: ThoughtForge — Multi-Profile Dockerfile
#
# Build with a specific hardware profile:
#   docker build --build-arg PROFILE=desktop_cpu -t thoughtforge:desktop .
#   docker build --build-arg PROFILE=pi_5        -t thoughtforge:pi5     .
#   docker build --build-arg PROFILE=phone_low   -t thoughtforge:phone   .
#
# Run:
#   docker run -it -v ./data:/app/data -v ./models:/app/models thoughtforge:desktop
#   docker run -it -v ./data:/app/data thoughtforge:desktop "What is Yggdrasil?"
#
# Data volume (/app/data): knowledge DB and memory files
# Models volume (/app/models): GGUF model files (optional)

ARG PROFILE=desktop_cpu
ARG PYTHON_VERSION=3.11

# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /build

# System deps for llama-cpp-python compilation and SQLite
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (cache layer)
COPY requirements.txt pyproject.toml setup.py ./
COPY src/ ./src/

# Install core Python dependencies (no llama-cpp-python — too heavy for base image)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        sqlalchemy \
        sentence-transformers \
        ijson \
        numpy \
        tqdm \
        pyyaml \
        click \
        rich \
        platformdirs && \
    pip install --no-cache-dir -e . --no-deps


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS runtime

ARG PROFILE=desktop_cpu
ENV THOUGHTFORGE_PROFILE=${PROFILE}
ENV THOUGHTFORGE_DATA_DIR=/app/data
ENV THOUGHTFORGE_MODELS_DIR=/app/models
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Runtime system deps (SQLite + curl for optional model fetch)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY src/ ./src/
COPY configs/ ./configs/
COPY hardware_profiles/ ./hardware_profiles/
COPY run_thoughtforge.py forge_memory.py ./
COPY pyproject.toml setup.py ./

# Reinstall package (editable link)
RUN pip install --no-cache-dir -e . --no-deps

# Create data and model volumes
RUN mkdir -p /app/data /app/models

VOLUME ["/app/data", "/app/models"]

# Healthcheck: verify Python import works
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from thoughtforge.cognition.core import ThoughtForgeCore; print('ok')" || exit 1

EXPOSE 8080

ENTRYPOINT ["python", "run_thoughtforge.py"]
CMD ["--profile", "${THOUGHTFORGE_PROFILE}"]
