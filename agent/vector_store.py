"""Qdrant local-mode storage with a no-op fallback when optional dependencies are absent."""

from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_URL, uuid5


class VectorStore:
    def __init__(self, path: str, collection: str):
        self.client = None
        self.collection = collection
        try:
            from qdrant_client import QdrantClient

            self.client = QdrantClient(path=path)
        except Exception as error:
            print(f"[Vector Store Disabled]: {error}")

    @property
    def available(self) -> bool:
        return self.client is not None

    def upsert(self, record_id: str, vector: list[float], payload: dict[str, Any]) -> bool:
        if not self.available or not vector:
            return False
        try:
            from qdrant_client.models import PointStruct, VectorParams, Distance

            if not self.client.collection_exists(self.collection):
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=len(vector), distance=Distance.COSINE),
                )

            self.client.upsert(
                collection_name=self.collection,
                points=[PointStruct(id=str(uuid5(NAMESPACE_URL, record_id)), vector=vector, payload=payload)],
            )
            return True
        except Exception as error:
            print(f"[Vector Store Write Error]: {error}")
            return False

    def search(self, vector: list[float], limit: int = 5) -> list[dict[str, Any]]:
        if not self.available or not vector:
            return []
        try:
            results = self.client.query_points(
                collection_name=self.collection,
                query=vector,
                limit=limit,
            ).points
            return [{"score": item.score, **(item.payload or {})} for item in results]
        except Exception as error:
            print(f"[Vector Store Search Error]: {error}")
            return []

    def clear(self) -> None:
        if not self.available:
            return
        try:
            self.client.delete_collection(self.collection)
        except Exception:
            pass