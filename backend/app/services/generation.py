import logging

import ollama

from app.services.retrieval import Hit

logger = logging.getLogger(__name__)

NOT_FOUND_MESSAGE = "I could not find this in the provided documents."

SYSTEM_PROMPT = f"""You are a document assistant. Answer the user's question using ONLY the context provided.

Rules:
- If the answer is not in the context, reply exactly: "{NOT_FOUND_MESSAGE}"
- After each statement, cite the context block(s) it came from, like [1] or [2].
- Never use outside knowledge. Never invent facts.
- Keep the answer clear and concise."""


def build_prompt(question: str, hits: list[Hit]) -> str:
    blocks = [
        f"[{i}] (source: {h.source}, page {h.page})\n{h.text}" for i, h in enumerate(hits, start=1)
    ]
    context = "\n\n".join(blocks)
    return f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer (with citations):"


def format_sources(hits: list[Hit]) -> list[str]:
    """Numbered to match the [1], [2] citations the LLM writes in its answer."""
    return [f"[{i}] {h.source} (page {h.page})" for i, h in enumerate(hits, start=1)]


class GenerationService:
    """Keeps ONE Ollama client for the whole app lifetime."""

    def __init__(self, host: str, model: str):
        self.model = model
        self.client = ollama.Client(host=host)
        logger.info("Ollama client ready (host=%s, model=%s)", host, model)

    def generate(self, question: str, hits: list[Hit]) -> str:
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(question, hits)},
            ],
            options={"temperature": 0.1},
        )
        return response["message"]["content"].strip()
