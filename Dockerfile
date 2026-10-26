# The agents (TP-SRS-161): one image, and APP_MODULE chooses which agent it runs.
#   APP_MODULE=agents.host.app:app        (the default)
#   APP_MODULE=agents.flight.app:app      agents.stay.app:app      agents.activities.app:app
FROM python:3.11.17-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# The self-hosted specialists read a Chroma index, so the optional packages are included.
COPY requirements/requirements.txt requirements/requirements-rag.txt requirements/
RUN pip install -r requirements/requirements-rag.txt

COPY shared/ shared/
COPY agents/ agents/
COPY logging.json ./
COPY data/rag/destinations.txt data/rag/destinations.txt

# The guidance index and the article cache live in a volume mounted at /data.
RUN useradd --create-home --uid 10001 agent \
    && mkdir -p /data/index /data/cache \
    && chown -R agent /data
USER agent

ENV APP_MODULE=agents.host.app:app PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn \"$APP_MODULE\" --host 0.0.0.0 --port \"$PORT\" --log-config logging.json"]
