"""The Flight, Stay, and Activities agents, built from one factory."""

import importlib
import logging
import time

from pydantic import ValidationError

from shared.config import Settings
from shared.llm import LLMError, LLMTimeout, create_llm_client
from shared.rag import create_retriever
from shared.rag.guidance import GUIDANCE_INSTRUCTION, render_guidance, sources_of
from shared.schemas import SPECIALISTS, TravelRequest
from shared.server import create_app
from shared.telemetry import create_metrics

UNAVAILABLE = {
    "flight": "Flight planner is temporarily unavailable.",
    "stay": "Stay planner is temporarily unavailable.",
    "activities": "Activity planner is temporarily unavailable.",
}

# Two or three suggestions each (SRS §1.2).
MAX_OFFERS = 3

# Every specialist's prompt carries this (TP-SRS-075).
NOT_LIVE_OR_BOOKABLE = (
    "These suggestions are illustrative only: they are not live availability, not live prices, "
    "and not bookable offers. Never present them as live or bookable."
)


def money(amount):
    """1500 -> "1500", 1500.5 -> "1500.50": whole amounts without decimals, never scientific notation."""
    return f"{amount:.0f}" if amount == int(amount) else f"{amount:.2f}"


def trip_summary(request):
    nights = (request.end_date - request.start_date).days
    return (
        f"Trip from {request.origin} to {request.destination}, "
        f"{request.start_date.isoformat()} to {request.end_date.isoformat()} ({nights} nights), "
        f"{request.travellers} travellers, total budget {money(request.budget)} {request.currency}."
    )


def build_messages(prompt, request, guidance=None):
    system = f"{prompt.ROLE} {NOT_LIVE_OR_BOOKABLE} Answer only with JSON that matches the given schema."
    user = f"{trip_summary(request)}\n\n{prompt.task(request)}"
    if guidance:
        user += f"\n\n{GUIDANCE_INSTRUCTION}\n\n{guidance}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def create_specialist_app(service, settings=None, metrics=None):
    settings = settings or Settings.from_env()
    metrics = metrics or create_metrics(service, settings)
    contract = SPECIALISTS[service]
    prompt = importlib.import_module(f"agents.{service}.prompt")
    llm = create_llm_client(settings)
    schema = contract.model_output.model_json_schema()
    logger = logging.getLogger(f"travel_planner.{service}")
    retriever = create_retriever(settings, llm, logger, metrics)
    app = create_app(service, settings, metrics=metrics)
    app.state.retriever = retriever

    async def ask_model(messages):
        """Ask the model for suggestions, recording the call's duration, outcome, and tokens."""
        start, outcome, result = time.perf_counter(), "error", None
        try:
            result = await llm.chat(messages, schema)
            suggestions = contract.model_output.model_validate(result.content)
            outcome = "success"
            return suggestions
        except LLMTimeout:
            outcome = "timeout"
            raise
        except ValidationError:
            outcome = "invalid"
            raise
        finally:
            tokens = (result.prompt_tokens, result.completion_tokens) if result else (0, 0)
            metrics.record_model_call(settings.llm_provider, outcome, time.perf_counter() - start, *tokens)

    @app.post("/run", response_model=contract.response)
    async def run(request: TravelRequest):
        guidance, used = render_guidance(await retriever.guidance(service, request.destination))
        try:
            suggestions = await ask_model(build_messages(prompt, request, guidance))
            offers = getattr(suggestions, contract.part)[:MAX_OFFERS]
            # Validated again as the full response, which needs at least one offer (TP-SRS-070, TP-SRS-072).
            # Sources come only from the index, never from the model (TP-SRS-090).
            return contract.response.model_validate(
                {contract.part: [offer.model_dump() for offer in offers], "sources": sources_of(used)}
            )
        except (LLMError, ValidationError) as error:
            logger.warning("Planning failed: %s: %s", type(error).__name__, error)
            return contract.response(error=UNAVAILABLE[service])

    return app
