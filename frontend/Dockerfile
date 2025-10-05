# Multi-stage Dockerfile for React/Vite frontend

# Development stage
FROM node:18-alpine AS development

WORKDIR /app

# Install dependencies first for better caching
COPY package*.json ./
RUN npm ci --only=production=false

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Development command (will be overridden by docker-compose)
CMD ["npm", "run", "dev"]

# Build stage
FROM node:18-alpine AS build

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production=false

# Copy source and build
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine AS production

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]