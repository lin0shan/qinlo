# 前端构建阶段（仅 build，不运行）
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Nginx 由 docker-compose 统一管理，此 Dockerfile 仅用于 CI 或单独构建
