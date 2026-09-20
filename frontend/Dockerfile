# ─────────────────────────────────────────────────────────────────
# BioLens Frontend Dockerfile
# React (Vite) — multi-stage: build → nginx static serve
# ─────────────────────────────────────────────────────────────────

# ── Stage 1: Build ───────────────────────────────────────────────
FROM node:20-alpine AS builder

LABEL stage="builder"

WORKDIR /app

# Copy package files first for Docker layer caching
COPY package.json package-lock.json ./

# Install dependencies (clean install, no dev artifacts in cache)
RUN npm ci --prefer-offline

# Copy source code
COPY . .

# Build production bundle
ARG VITE_API_URL=http://localhost:10000
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build


# ── Stage 2: Serve with Nginx ─────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

LABEL maintainer="Mahbub Ul Alam Bhuiyan & Mahir Ahamed Rohan"
LABEL description="BioLens Frontend — React + Vite served by Nginx"

# Remove default nginx static files
RUN rm -rf /usr/share/nginx/html/*

# Copy built React app from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config: serve SPA, proxy /api/* to backend
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
