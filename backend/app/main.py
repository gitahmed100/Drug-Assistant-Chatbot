import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.query import router as query_router
from app.core.config import settings
from app.services.generation import GenerationService
from app.services.retrieval import RetrievalService
from app.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs ONCE when the server starts: load heavy things here, not per request.
    setup_logging(settings.log_level)
    logger.info("Starting up...")
    app.state.retrieval = RetrievalService(settings.vector_store_dir)
    app.state.generation = GenerationService(settings.ollama_host, settings.ollama_model)
    yield
    logger.info("Shutting down.")


app = FastAPI(title="RAG Document Assistant", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router)
