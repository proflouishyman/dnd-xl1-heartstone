FROM nginx:alpine

# Static site baked into the image (immutable; rebuild to update content).
COPY . /usr/share/nginx/html/

# Proxy /api/ and the realtime WebSocket to the dnd-api sidecar; everything else
# is served as static files. Persistent character-sheet state lives in dnd-api +
# the dnd_data volume, never in this image.
COPY deploy/default.conf /etc/nginx/conf.d/default.conf
