# Standalone Odin Anchor — the queue/auth/webhook "door" third parties knock on, deployed on the VM.
# It uses ONLY the Python standard library (http.server) plus the anchor_queue/integrations modules,
# so the image is tiny and needs no pip install. Credentials are NOT baked in — mount oth/.cred at run.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Only the pieces the standalone anchor actually needs (not the whole brain server).
COPY server/ /app/server/

EXPOSE 9100
WORKDIR /app/server
# host/port overridable at runtime; defaults match the Phase-2 stand-in contract.
CMD ["python3", "anchor_remote.py", "--host", "0.0.0.0", "--port", "9100"]
