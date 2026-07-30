FROM python:3.12.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app app
COPY app/requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt
COPY --chown=app:app app/app.py .
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/livez')"]
CMD ["gunicorn", "--bind=0.0.0.0:8080", "--workers=1", "--threads=4", "--access-logfile=-", "--error-logfile=-", "app:app"]
