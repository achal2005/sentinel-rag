# Sentinel operator console image. Build context = repo root:
#   docker build -f frontend/Dockerfile -t sentinel-frontend .
# Relies on next.config.ts `output: "standalone"`.
FROM node:20-slim AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:20-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./
RUN npm run build

FROM node:20-slim AS run
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0
# Standalone server bundle + static assets + public files.
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
# Real eval numbers for the landing / usage pages (app/api/evals/route.ts reads
# ./evals/reports/latest.json relative to the server's working directory).
COPY evals/reports/latest.json ./evals/reports/latest.json
EXPOSE 3000
CMD ["node", "server.js"]
