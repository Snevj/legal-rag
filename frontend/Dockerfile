FROM node:20-slim AS deps

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-slim AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Baked in at build time since Next.js inlines NEXT_PUBLIC_* vars into the
# client bundle - it can't be swapped at container start like a normal env
# var. Defaults to same-origin /api, matching the reverse-proxy setup in
# docker-compose.prod.yml where nginx forwards /api/* to the backend
# container, so the built-in default works without rebuilding for most
# deployments.
ARG NEXT_PUBLIC_API_BASE_URL=/api
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

RUN npm run build

FROM node:20-slim

WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
