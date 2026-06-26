# ====================================================================
# Healthcare AI Router — Frontend Dockerfile
# Production-grade multi-stage build (Node build + Nginx serve)
# ====================================================================

# ── Stage 1: Builder ────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first for optimal layer caching
COPY package*.json ./
RUN npm ci --silent

# Copy source and build
COPY . .
RUN npm run build

# ── Stage 2: Serve via Nginx ─────────────────────────────────────────
FROM nginx:alpine AS runtime

LABEL maintainer="Healthcare AI Router"
LABEL version="1.0.0"

# Copy compiled assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/health.txt || exit 1

CMD ["nginx", "-g", "daemon off;"]
