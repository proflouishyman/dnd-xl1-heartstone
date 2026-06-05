FROM nginx:alpine

# Static site baked into the image (immutable; rebuild to update content).
COPY . /usr/share/nginx/html/

# /data is provided by a named docker volume (see docker-compose.yml) and is
# reserved for future mutable state (e.g. player character renames) that must
# persist across rebuilds and is intentionally NOT part of the repo/image.
