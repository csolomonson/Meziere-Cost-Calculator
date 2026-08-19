FROM node:22.23.1-bookworm-slim AS frontend
WORKDIR /build
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY frontend ./frontend
COPY tools/build-frontend.mjs ./tools/build-frontend.mjs
RUN pnpm test && pnpm run build

FROM caddy:2.11.4-alpine AS caddy

FROM python:3.13.13-slim-bookworm AS runtime

ARG DEBIAN_FRONTEND=noninteractive
ARG APP_VERSION=development
ARG VCS_REF=unknown
ARG VCS_URL=https://github.com/csolomonson/Meziere-Cost-Calculator
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl gnupg unixodbc \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/microsoft-prod.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
COPY --from=frontend /build/static/dist ./static/dist
COPY --from=caddy /usr/bin/caddy /usr/bin/caddy

RUN addgroup --system --gid 10001 costapp \
    && adduser --system --uid 10001 --ingroup costapp costapp \
    && mkdir -p \
        /var/lib/cost-calculator/config \
        /var/lib/cost-calculator/secrets \
        /var/lib/cost-calculator/users \
        /var/lib/cost-calculator/ca \
        /var/lib/cost-calculator/database \
        /var/lib/cost-calculator/caddy/data \
        /var/lib/cost-calculator/caddy/config \
        /var/lib/cost-calculator/update \
        /usr/local/share/cost-calculator \
    && cp /etc/ssl/certs/ca-certificates.crt /usr/local/share/cost-calculator/ca-certificates.crt \
    && cp /usr/local/share/cost-calculator/ca-certificates.crt /var/lib/cost-calculator/ca/ca-certificates.crt \
    && rm /etc/ssl/certs/ca-certificates.crt \
    && ln -s /var/lib/cost-calculator/ca/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt \
    && chmod +x \
        /app/deployment/configure-container.sh \
        /app/deployment/configure-image.sh \
        /app/deployment/container-entrypoint.sh \
        /app/deployment/start-app.sh \
    && chown -R costapp:costapp /app /var/lib/cost-calculator \
    && chmod 0644 /usr/local/share/cost-calculator/ca-certificates.crt
USER costapp

LABEL org.opencontainers.image.title="Meziere Cost Calculator" \
      org.opencontainers.image.description="Single-container HTTPS product cost calculator" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.source="$VCS_URL"

ENV PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    APP_VERSION="$APP_VERSION" \
    APP_REPOSITORY="$VCS_URL" \
    COST_APP_STATE_ROOT=/var/lib/cost-calculator \
    COST_APP_USERS_JSON_FILE=/var/lib/cost-calculator/users/app_users.json \
    COST_DB_PASSWORD_FILE=/var/lib/cost-calculator/secrets/db_password.txt \
    UPDATE_STATUS_FILE=/var/lib/cost-calculator/update/update-status.json \
    UPDATE_REQUEST_FILE=/var/lib/cost-calculator/update/update-request.json \
    SSL_CERT_FILE=/var/lib/cost-calculator/ca/ca-certificates.crt \
    XDG_DATA_HOME=/var/lib/cost-calculator/caddy/data \
    XDG_CONFIG_HOME=/var/lib/cost-calculator/caddy/config

EXPOSE 8443
HEALTHCHECK --interval=15s --timeout=6s --start-period=10s --retries=8 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/ready', timeout=4)"
STOPSIGNAL SIGTERM
ENTRYPOINT ["/app/deployment/container-entrypoint.sh"]
CMD ["serve"]
