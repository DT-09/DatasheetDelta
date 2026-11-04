FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATASHEETDELTA_DB=/data/datasheetdelta.sqlite3
WORKDIR /app
COPY pyproject.toml README.md ./
COPY datasheetdelta ./datasheetdelta
COPY web ./web
RUN pip install --no-cache-dir '.[api,documents]' && mkdir -p /data
VOLUME ["/data"]
EXPOSE 8000
CMD ["uvicorn","datasheetdelta.api:app","--host","0.0.0.0","--port","8000"]
