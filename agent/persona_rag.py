"""Local persona retrieval using Qdrant when available and keyword fallback otherwise."""

from __future__ import annotations

import re
from pathlib import Path

from agent.vector_store import VectorStore
from config import EMBEDDING_MODEL, MEMORY_RETRIEVAL_LIMIT, MEMORY_RETRIEVAL_MAX_CHARS
from config import VECTOR_COLLECTION, VECTOR_DB_PATH
from perception.llm_client import embed_ollama


class PersonaRAG:
    def __init__(self, directory: str = "persona", store: VectorStore | None = None):
        self.directory = Path(directory)
        self.store = store or VectorStore(VECTOR_DB_PATH, VECTOR_COLLECTION)
        self.documents = self._load_documents()
        self._indexed = False

    def _load_documents(self) -> list[str]:
        if not self.directory.exists():
            return []
        return [path.read_text(encoding="utf-8") for path in sorted(self.directory.glob("*.md"))]

    def _ensure_index(self) -> None:
        if self._indexed:
            return
        for index, document in enumerate(self.documents):
            self.store.upsert(
                f"persona-{index}",
                embed_ollama(document, EMBEDDING_MODEL),
                {"kind": "persona", "text": document},
            )
        self._indexed = True

    def retrieve(self, query: str, limit: int = MEMORY_RETRIEVAL_LIMIT,
                 max_chars: int = MEMORY_RETRIEVAL_MAX_CHARS) -> str:
        self._ensure_index()
        vector_results = self.store.search(embed_ollama(query, EMBEDDING_MODEL), limit)
        if vector_results:
            matches = [item.get("text", "") for item in vector_results]
        else:
            terms = set(re.findall(r"[\w\u4e00-\u9fff]+", query.lower()))
            matches = sorted(
                self.documents,
                key=lambda text: sum(text.lower().count(term) for term in terms),
                reverse=True,
            )[:limit] if terms else []
        return "\n\n".join(matches)[:max_chars]