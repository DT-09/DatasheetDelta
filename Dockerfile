FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATASHEETDELTA_DB=/data/datasheetdelta.sqlite3

WORKDIR /app
COPY pyproject.toml README.md ./
COPY datasheetdelta ./datasheetdelta
COPY web ./web
COPY examples ./examples

RUN pip install --no-cache-dir '.[api,documents]' \
    && mkdir -p /data \
    && addgroup --system app \
    && adduser --system --ingroup app --no-create-home app \
    && chown -R app:app /app /data

USER app
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"
CMD ["uvicorn","datasheetdelta.api:app","--host","0.0.0.0","--port","8000"]
