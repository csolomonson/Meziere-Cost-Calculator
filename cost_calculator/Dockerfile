FROM node:22.23.1-bookworm-slim AS frontend
WORKDIR /build
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY frontend ./frontend
COPY tools/build-frontend.mjs ./tools/build-frontend.mjs
RUN pnpm run build

FROM python:3.13.13-slim-bookworm AS runtime

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg unixodbc \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/microsoft-prod.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Optional private CA certificates make encrypted SQL Server connections work
# without weakening certificate validation. Only files ending in .crt are used.
COPY deployment/sql-ca/ /usr/local/share/ca-certificates/cost-calculator/
RUN update-ca-certificates

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
COPY --from=frontend /build/static/dist ./static/dist

RUN addgroup --system costapp && adduser --system --ingroup costapp costapp \
    && mkdir -p /var/lib/cost-app /var/lib/cost-app-users \
    && chmod +x /app/deployment/start-app.sh \
    && chown -R costapp:costapp /app /var/lib/cost-app /var/lib/cost-app-users
USER costapp

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["/app/deployment/start-app.sh"]
