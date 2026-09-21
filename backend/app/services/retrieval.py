import json
import logging
from dataclasses import dataclass
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class Hit:
    text: str
    source: str
    page: int
    score: float  # cosine similarity: higher = more similar


class RetrievalService:
    """Loads the vector store ONCE (at startup) and answers similarity searches."""

    def __init__(self, vector_store_dir: str):
        store_dir = Path(vector_store_dir)
        config_path = store_dir / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(
                f"{config_path} not found. Run the notebook first so it exports the vector store "
                f"into backend/data/vector_store/."
            )

        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        logger.info("Loading embedding model: %s", self.config["embedding_model"])
        self.embedder = SentenceTransformer(self.config["embedding_model"])

        client = chromadb.PersistentClient(path=str(store_dir))
        self.collection = client.get_collection(self.config["collection_name"])
        logger.info("Vector store loaded: %d chunks", self.collection.count())

    def retrieve(self, question: str, top_k: int) -> list[Hit]:
        query_embedding = self.embedder.encode([question], normalize_embeddings=True).tolist()
        result = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        hits = []
        for text, meta, distance in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        ):
            hits.append(
                Hit(text=text, source=meta["source"], page=int(meta["page"]), score=1 - distance)
            )
        return hits
