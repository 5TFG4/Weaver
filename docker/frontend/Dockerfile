# Production Dockerfile for Haro Frontend
FROM node:20-bookworm AS builder
WORKDIR /app

# Install dependencies
COPY haro/package*.json ./
RUN npm ci

# Build the app
COPY haro/ ./
RUN npm run build

# Production image with nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
