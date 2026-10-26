# The agents (TP-SRS-161): one image, and APP_MODULE chooses which agent it runs.
#   APP_MODULE=agents.host.app:app        (the default)
#   APP_MODULE=agents.flight.app:app      agents.stay.app:app      agents.activities.app:app

# Build stage: install the pinned dependencies into a virtual environment.
FROM python:3.11.17-slim-bookworm AS build

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# The runtime requirements, plus the optional Chroma packages the self-hosted specialists read
# their index with. requirements-rag.txt holds only the Chroma packages, so both are needed.
COPY requirements/requirements.txt requirements/requirements-rag.txt /tmp/requirements/
RUN pip install -r /tmp/requirements/requirements.txt -r /tmp/requirements/requirements-rag.txt

# Runtime stage: the same Python, the virtual environment, and the application code only.
FROM python:3.11.17-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# The guidance index and the article cache live in a volume mounted at /data.
RUN useradd --create-home --uid 10001 agent \
    && mkdir -p /data/index /data/cache \
    && chown -R agent /data

COPY --from=build /opt/venv /opt/venv
COPY shared/ shared/
COPY agents/ agents/
COPY logging.json ./
COPY data/rag/destinations.txt data/rag/destinations.txt

USER agent

ENV APP_MODULE=agents.host.app:app PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn \"$APP_MODULE\" --host 0.0.0.0 --port \"$PORT\" --log-config logging.json"]
