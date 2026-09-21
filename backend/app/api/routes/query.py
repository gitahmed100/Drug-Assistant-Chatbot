import logging

from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.schemas.query import QueryRequest, QueryResponse
from app.services.generation import NOT_FOUND_MESSAGE, format_sources

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "llm_model": settings.ollama_model}


# NOTE: plain `def` (not `async def`) on purpose: embedding + LLM calls are blocking,
# and FastAPI runs plain `def` endpoints in a thread pool so the server stays responsive.
@router.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest, request: Request):
    retrieval = request.app.state.retrieval
    generation = request.app.state.generation

    hits = retrieval.retrieve(payload.question, settings.top_k)
    logger.info("Question=%r | best score=%.2f", payload.question, hits[0].score if hits else 0)

    # Guardrail: nothing relevant found -> do NOT let the LLM improvise.
    if not hits or hits[0].score < settings.min_score:
        return QueryResponse(answer=NOT_FOUND_MESSAGE, sources=[])

    try:
        answer = generation.generate(payload.question, hits)
    except Exception:
        logger.exception("LLM call failed")
        raise HTTPException(
            status_code=503,
            detail="The language model is not available. Is Ollama running?",
        )

    return QueryResponse(answer=answer, sources=format_sources(hits))
