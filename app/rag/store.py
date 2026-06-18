"""Простое RAG-хранилище на эмбеддингах.

Без тяжёлых векторных БД: для базы знаний салона (пара десятков кусочков)
обычного косинусного сходства в памяти более чем достаточно.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

# куда складываем посчитанный индекс
INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "index.json"


def split_into_chunks(text: str) -> list[str]:
    # режем базу по заголовкам (#, ##, ###): один блок-вопрос = один чанк
    parts = re.split(r"\n(?=#{1,3}\s)", text)
    chunks = []
    for part in parts:
        part = part.strip()
        if len(part) > 5:  # совсем пустые/мелкие куски выкидываем
            chunks.append(part)
    return chunks


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class KnowledgeBase:
    def __init__(self, chunks: list[str], vectors: list[list[float]]) -> None:
        self._chunks = chunks
        self._vectors = vectors

    def __len__(self) -> int:
        return len(self._chunks)

    @classmethod
    def load(cls) -> "KnowledgeBase":
        if not INDEX_PATH.exists():
            raise RuntimeError(
                "Индекс не найден. Сначала собери его: python -m scripts.build_index"
            )
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        return cls(data["chunks"], data["vectors"])

    def reload(self) -> int:
        """Перечитать индекс с диска в тот же объект — используем после пересборки из админки."""
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        self._chunks = data["chunks"]
        self._vectors = data["vectors"]
        return len(self._chunks)

    @staticmethod
    def save(chunks: list[str], vectors: list[list[float]]) -> None:
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {"chunks": chunks, "vectors": vectors}
        INDEX_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def search(self, query_vec: list[float], top_k: int) -> list[tuple[float, str]]:
        scored = [
            (cosine(query_vec, vec), chunk)
            for chunk, vec in zip(self._chunks, self._vectors)
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[:top_k]
