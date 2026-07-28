FROM python:3.14-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install .

FROM python:3.14-slim AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ANALYSIS_PATH=/app/reports/demo-analysis.json

RUN groupadd --system --gid 10001 processapp \
    && useradd --system --uid 10001 --gid processapp --home /nonexistent processapp

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY data ./data
COPY reports ./reports

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]
CMD ["uvicorn", "process_optimizer.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
