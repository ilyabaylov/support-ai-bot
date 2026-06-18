"""Сборка векторного индекса из базы знаний.

Вынесли отдельно, потому что индекс собирается из двух мест:
  • скриптом перед первым запуском (python -m scripts.build_index);
  • из админки по кнопке «Обновить базу» — без перезапуска бота.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.rag.store import KnowledgeBase, split_into_chunks
from app.services.gemini import Gemini

KB_FILE = Path(__file__).resolve().parents[2] / "knowledge_base" / "faq.md"


async def build_index(gemini: Gemini) -> int:
    """Читает faq.md, считает эмбеддинги, сохраняет индекс. Возвращает число кусков."""
    text = KB_FILE.read_text(encoding="utf-8")
    chunks = split_into_chunks(text)
    if not chunks:
        raise RuntimeError("База знаний пустая — нечего индексировать.")
    vectors = await gemini.embed(chunks)
    KnowledgeBase.save(chunks, vectors)
    return len(chunks)


def list_topics() -> list[str]:
    """Заголовки разделов базы — для кнопки «Темы базы» в админке."""
    text = KB_FILE.read_text(encoding="utf-8")
    return re.findall(r"^#{1,3}\s+(.+)$", text, flags=re.MULTILINE)
