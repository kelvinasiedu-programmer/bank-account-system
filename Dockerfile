# ---------- build stage ----------
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- runtime stage ----------
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /install /usr/local
COPY src/ src/
COPY pyproject.toml .

RUN mkdir -p data

ENV PYTHONUNBUFFERED=1
ENV STORAGE_PATH=/app/data/accounts.json

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/api/v1/health')"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]
