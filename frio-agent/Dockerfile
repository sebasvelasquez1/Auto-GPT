# Frío dashboard — container image for hosting the read-only dashboard.
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY frio ./frio
RUN pip install ".[deploy]"

# The host injects $PORT; default 8787 for local `docker run`.
EXPOSE 8787
CMD ["sh", "-c", "frio dashboard --host 0.0.0.0 --port ${PORT:-8787}"]
