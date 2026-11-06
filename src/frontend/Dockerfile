# Frontend: build Angular (production) → phục vụ bằng nginx-unprivileged (non-root, cổng 8080). Base ghim theo digest (ECR Public).
ARG NODE_IMAGE=public.ecr.aws/docker/library/node:22-alpine@sha256:fe4f6d74e20370acb04ad889077d14d0f64a9c8ea6a42bc60cddf1e844699914
ARG NGINX_IMAGE=public.ecr.aws/nginx/nginx-unprivileged:1.30-alpine@sha256:44e74ca483234093081138b6d7b6f561d55557756a2deefc3a5056148defeb99

FROM ${NODE_IMAGE} AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --legacy-peer-deps --no-audit --no-fund
COPY angular.json tsconfig.json tsconfig.app.json ./
COPY public ./public
COPY src ./src
RUN npx ng build --configuration production

FROM ${NGINX_IMAGE} AS runtime
# Vá gói Alpine đã có bản sửa (quét: scripts/scan-images.sh), rồi trở lại user nginx (101) không phải root
USER root
RUN apk upgrade --no-cache
USER 101
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/culture-atlas-web/browser /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/"]
