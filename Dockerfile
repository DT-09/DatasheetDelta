FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY datasheetdelta ./datasheetdelta
COPY web ./web
RUN pip install --no-cache-dir '.[api,documents]'
EXPOSE 8000
CMD ["uvicorn","datasheetdelta.api:app","--host","0.0.0.0","--port","8000"]
