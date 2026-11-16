# syntax=docker/dockerfile:1
# hotstar web (Angular) - multi-stage: build with Node, serve static files + reverse-proxy /api with nginx.

FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime
# nginx renders this template at start-up, substituting only GATEWAY_* variables
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist/hotstar-web/browser /usr/share/nginx/html
ENV GATEWAY_URL=http://api-gateway:8000 NGINX_ENVSUBST_FILTER=GATEWAY_
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 CMD wget -qO- http://127.0.0.1:8080/healthz >/dev/null || exit 1
