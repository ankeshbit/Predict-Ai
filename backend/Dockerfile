# Multi-stage Dockerfile for FastAPI Backend
FROM python:3.10-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY ml/ ml/
COPY backend/ backend/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ./ml && \
    pip install --no-cache-dir -e ./backend

FROM python:3.10-slim AS runner

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY backend/ /app/backend/
COPY ml/ /app/ml/

WORKDIR /app/backend

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
