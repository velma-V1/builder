FROM node:24.18.0-bookworm-slim AS build

ARG WORLDMONITOR_COMMIT
LABEL org.opencontainers.image.revision=$WORLDMONITOR_COMMIT
RUN apt-get update \
    && apt-get install --yes --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --filter=blob:none https://github.com/koala73/worldmonitor.git /app \
    && git -C /app checkout --detach "${WORLDMONITOR_COMMIT}" \
    && test "$(git -C /app rev-parse HEAD)" = "${WORLDMONITOR_COMMIT}"
WORKDIR /app
RUN npm ci

FROM node:24.18.0-bookworm-slim
ARG WORLDMONITOR_COMMIT
LABEL org.opencontainers.image.revision=$WORLDMONITOR_COMMIT
COPY --from=build --chown=node:node /app /app
WORKDIR /app
USER node
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
