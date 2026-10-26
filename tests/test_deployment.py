"""Deployment configuration checks: Docker Compose, the container images, and Vercel (TDD plan §5).

These automate the inspections of TP-SRS-113, 142, 144, 161, 164 to 166, 183, and 188. Whether the
deployed services behave this way is checked by hand (docs/RELEASE_CHECKLIST.md).
"""

import json
import re
from pathlib import Path

import pytest
import yaml
from uvicorn.importer import import_from_string

from shared.config import PROVIDER_DEFAULTS, WEB_TIMEOUT_SECONDS

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
SERVICES = COMPOSE["services"]
VERCEL = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
SPECIALISTS = ("flight", "stay", "activities")
EXACT_TAG = re.compile(r":\d+\.\d+\.\d+(-[a-z0-9.-]+)?$")


def env(service):
    return SERVICES[service].get("environment", {})


# TP-SRS-113, TP-SRS-165: only the web application and the Host can be reached from outside.
def test_only_web_and_host_publish_ports():
    published = {name for name, service in SERVICES.items() if service.get("ports")}
    assert published == {"web", "host"}
    for specialist in SPECIALISTS:
        assert SERVICES[specialist]["expose"] == ["8000"]


# TP-SRS-144: the chat and embedding models stay loaded together for at least 30 minutes.
def test_ollama_keeps_both_models_loaded():
    settings = env("ollama")
    assert re.fullmatch(r"(\d+)m", settings["OLLAMA_KEEP_ALIVE"]) and int(settings["OLLAMA_KEEP_ALIVE"][:-1]) >= 30
    assert int(settings["OLLAMA_MAX_LOADED_MODELS"]) >= 2


# The models downloaded are the ones the agents use by default.
def test_models_service_pulls_default_models():
    chat_model, embedding_model, _ = PROVIDER_DEFAULTS["ollama"]
    command = " ".join(SERVICES["models"]["entrypoint"])
    assert f"ollama pull {chat_model}" in command
    assert f"ollama pull {embedding_model}" in command


# TP-SRS-183: each service receives only the secrets it uses.
def test_secrets_only_where_used():
    holders = {secret: {name for name in SERVICES if secret in env(name)} for secret in ("HOST_API_KEY", "OPENAI_API_KEY", "OTEL_EXPORTER_OTLP_HEADERS")}
    assert holders["HOST_API_KEY"] == {"host", "web"}
    assert holders["OPENAI_API_KEY"] == set()
    assert holders["OTEL_EXPORTER_OTLP_HEADERS"] == {"host", *SPECIALISTS}


# TP-SRS-188: the self-hosted stack uses no paid service.
def test_self_hosted_uses_local_models_only():
    for name in (*SPECIALISTS, "ingest"):
        assert env(name)["LLM_PROVIDER"] == "ollama"
        assert env(name)["OLLAMA_BASE_URL"] == "http://ollama:11434"


# TP-SRS-142: the Host waits longer than a model call, and less than the web application waits.
def test_timeouts_nest():
    downstream = float(env("host")["DOWNSTREAM_TIMEOUT_SECONDS"])
    for specialist in SPECIALISTS:
        assert float(env(specialist)["LLM_TIMEOUT_SECONDS"]) < downstream < WEB_TIMEOUT_SECONDS


# TP-SRS-161: one image, with APP_MODULE choosing the agent.
def test_agents_share_one_image():
    images = {SERVICES[name]["image"] for name in ("host", *SPECIALISTS, "ingest")}
    assert len(images) == 1
    modules = {name: env(name)["APP_MODULE"] for name in ("host", *SPECIALISTS)}
    assert modules == {name: f"agents.{name}.app:app" for name in modules}


# The Host finds each specialist at its Compose service name.
def test_host_reaches_specialists_by_service_name():
    for specialist in SPECIALISTS:
        assert env("host")[f"{specialist.upper()}_SERVICE_URL"] == f"http://{specialist}:8000"
    assert env("web")["HOST_SERVICE_URL"] == "http://host:8000"


# TP-SRS-166: container images are pinned to exact versions.
def test_container_images_pinned():
    froms = [
        line.split()[1]
        for dockerfile in (ROOT / "Dockerfile", ROOT / "web" / "Dockerfile")
        for line in dockerfile.read_text(encoding="utf-8").splitlines()
        if line.startswith("FROM ")
    ]
    pulled = [service["image"] for service in SERVICES.values() if "build" not in service]
    assert froms and pulled
    unpinned = [image for image in froms + pulled if not EXACT_TAG.search(image)]
    assert unpinned == []


# TP-SRS-161: the agents run Python 3.11.
def test_agent_image_uses_python_311():
    first = (ROOT / "Dockerfile").read_text(encoding="utf-8").split("FROM ", 1)[1].split()[0]
    assert first.startswith("python:3.11.")


# The agent image installs the runtime requirements as well as the Chroma ones, which hold
# only Chroma and its dependencies.
def test_agent_image_installs_runtime_requirements():
    installs = [line for line in (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines() if "pip install" in line]
    assert any("requirements.txt" in line.replace("requirements-rag.txt", "") for line in installs)
    assert any("requirements-rag.txt" in line for line in installs)


# TP-SRS-182: the web image's build context leaves out secrets and local installs.
def test_web_image_ignores_secrets():
    lines = (ROOT / "web" / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert "**/.env*" in lines and "!**/.env.example" in lines and "node_modules" in lines


# TP-SRS-165: on Vercel, public routes lead only to the web application and the Host.
def test_vercel_public_routes():
    destinations = [rewrite["destination"]["service"] for rewrite in VERCEL["rewrites"]]
    assert set(destinations) == {"web", "host"}
    # The catch-all comes last, so the Host's routes are matched first.
    assert VERCEL["rewrites"][-1] == {"source": "/(.*)", "destination": {"service": "web"}}
    assert set(VERCEL["services"]) == {"web", "host", *SPECIALISTS}


# TP-SRS-165: the specialists are private, reached by the Host through bindings whose variables
# are the ones the settings read.
def test_vercel_bindings_match_settings():
    def bindings(service):
        return {b["env"]: b["service"] for b in VERCEL["services"][service].get("bindings", [])}

    assert bindings("host") == {f"{s.upper()}_SERVICE_URL": s for s in SPECIALISTS}
    assert bindings("web") == {"HOST_SERVICE_URL": "host"}
    for specialist in SPECIALISTS:
        assert bindings(specialist) == {}
    for service in VERCEL["services"].values():
        for binding in service.get("bindings", []):
            assert (binding["type"], binding["format"]) == ("service", "url")


# The Vercel entrypoints are the same apps APP_MODULE names.
@pytest.mark.parametrize("service", ["host", *SPECIALISTS])
def test_vercel_entrypoints_import(service):
    entrypoint = VERCEL["services"][service]["entrypoint"]
    assert entrypoint == f"agents.{service}.app:app"
    assert import_from_string(entrypoint)
