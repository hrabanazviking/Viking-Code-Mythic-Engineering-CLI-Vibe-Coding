# syntax=docker/dockerfile:1.7
# Mythic Vibe CLI — multi-arch container image (PH-21.1).
#
# Two-stage build:
#   1. builder  — installs the project + the [ai,otel,ux,tui] extras
#                 into an isolated /opt/venv. Build deps stay in this
#                 stage and are discarded.
#   2. runtime  — copies /opt/venv into a slim base image and sets the
#                 mythic-vibe entrypoint. Runs as a non-root user.
#
# Triggered by .github/workflows/release-oci.yml on v*.*.* tag pushes.
# Multi-arch (linux/amd64 + linux/arm64) via buildx + QEMU.
#
# Image surface:
#   ENTRYPOINT ["mythic-vibe"]   default args: --help
#   USER mythic                  (uid 1000)
#   WORKDIR /work                operator's project mount point
#
# Why no shell-form ENTRYPOINT: exec-form keeps PID 1 mythic-vibe so
# Ctrl-C / docker stop deliver SIGINT/SIGTERM directly to the CLI.

# -------- builder stage --------------------------------------------------

FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# Build deps for any wheel that needs to compile from sdist on arm64
# (most pure-Python wheels publish arm64 binaries; this is insurance).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        git \
    && rm -rf /var/lib/apt/lists/*

# Create the venv where the project + extras land.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /src

# Copy the bare-minimum pip needs first so the dependency layer
# caches across iterations where only docs / tests change.
COPY pyproject.toml README.md LICENSE ./
COPY mythic_vibe_cli ./mythic_vibe_cli

# Install with the v1.0 default extras enabled. Operators who want
# a slimmer image rebuild from the same Dockerfile passing their
# own extras list via --build-arg (see docs/INSTALL.md "Container").
RUN pip install --upgrade pip \
    && pip install ".[ai,otel,ux,tui]"

# Strip bytecode caches so the runtime stage is smaller.
RUN find /opt/venv -name "__pycache__" -type d -exec rm -rf {} + \
    && find /opt/venv -name "*.pyc" -delete


# -------- runtime stage --------------------------------------------------

FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="mythic-vibe-cli" \
      org.opencontainers.image.description="Beginner-friendly CLI that enforces Mythic Engineering vibe-coding workflow" \
      org.opencontainers.image.source="https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding" \
      org.opencontainers.image.documentation="https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/blob/main/docs/INSTALL.md" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.vendor="Mythic Vibe Contributors"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

# Non-root user. uid 1000 matches the conventional first non-root
# uid on most Linux distros, so a host bind-mount of an operator's
# project directory works without chown gymnastics.
RUN groupadd --gid 1000 mythic \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash mythic

COPY --from=builder /opt/venv /opt/venv

USER mythic
WORKDIR /work

# Smoke verifying the venv came across correctly. Catches a broken
# build before the image ever lands in a registry.
RUN mythic-vibe --version

ENTRYPOINT ["mythic-vibe"]
CMD ["--help"]
