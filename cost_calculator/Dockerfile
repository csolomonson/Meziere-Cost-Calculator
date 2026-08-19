FROM node:22.23.1-bookworm-slim AS frontend
WORKDIR /build
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY frontend ./frontend
COPY tools/build-frontend.mjs ./tools/build-frontend.mjs
RUN pnpm test && pnpm run build

FROM python:3.13.13-slim-bookworm AS runtime

ARG DEBIAN_FRONTEND=noninteractive
ARG APP_VERSION=development
ARG VCS_REF=unknown
ARG VCS_URL=https://github.com/csolomonson/Meziere-Cost-Calculator
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg unixodbc \
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

RUN addgroup --system --gid 10001 costapp \
    && adduser --system --uid 10001 --ingroup costapp costapp \
    && mkdir -p /var/lib/cost-app /var/lib/cost-app-users \
    && chmod +x /app/deployment/configure-container.sh /app/deployment/start-app.sh \
    && chown -R costapp:costapp /app /var/lib/cost-app /var/lib/cost-app-users
USER costapp

LABEL org.opencontainers.image.title="Meziere Cost Calculator" \
      org.opencontainers.image.description="Authenticated product cost calculator" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.source="$VCS_URL"

ENV PYTHONUNBUFFERED=1 \
    APP_VERSION="$APP_VERSION" \
    APP_REPOSITORY="$VCS_URL"
EXPOSE 8000
CMD ["/app/deployment/start-app.sh"]
