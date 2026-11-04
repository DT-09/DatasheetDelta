# Deployment guide

## Recommended first deployment

The product is a single FastAPI service that serves both the browser interface and its API. Deploy the container, not only the static HTML files.

Requirements:
- Docker Engine and Docker Compose v2.
- A persistent volume for SQLite.
- A long random bearer token.
- TLS termination and restricted network access before public exposure.

## Build and run

Generate a token and export it in your shell:

    # macOS/Linux
    export DATASHEETDELTA_ACCESS_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"

    # PowerShell
    $env:DATASHEETDELTA_ACCESS_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(48))"

Then:

    docker compose build
    docker compose up -d
    docker compose ps

Open the service on port 8000 behind a trusted TLS reverse proxy. Enter the bearer token in the workspace. The container runs as a non-root user and stores its SQLite database in the named volume datasheetdelta-data.

Do not expose port 8000 directly to the public internet without TLS, firewall rules and a deployment security review.

## Cloudflare note

Cloudflare Pages can host static assets, but it does not run this Python FastAPI application. A Pages-only deployment will not provide the comparison API or SQLite review ledger. For a Cloudflare-fronted deployment, run the Docker service on a Python-capable host and place a TLS-protected Cloudflare proxy in front of it. The current app serves UI and API from the same origin; a separate Pages frontend is not a supported configuration.

## Database backup

Stop the service before copying the SQLite volume so the database and WAL state remain consistent:

    docker compose stop
    docker run --rm -v datasheetdelta-data:/data -v "$PWD/backups:/backup" alpine sh -c "tar czf /backup/datasheetdelta-data.tar.gz -C /data ."
    docker compose start

Store backups with the same access restrictions as the source engineering data. Test restoration before relying on a backup.

## Operations

- Rotate the bearer token by changing DATASHEETDELTA_ACCESS_TOKEN and restarting the service.
- Keep the SQLite volume persistent across container upgrades.
- Monitor disk usage, container logs, health status and backup success.
- Review retention needs. Deleting an investigation removes its extracted report and all review events.
- The app does not implement per-person identity, role-based access, rate limiting, encrypted database storage or parser sandboxing.
- Review reverse-proxy request logging; do not log authorization headers or uploaded request bodies.

## Rollback

Keep the previous container image and a verified database backup before upgrading. Stop the service, restore the prior image and database snapshot, then verify /api/health and a synthetic comparison before reopening access.
