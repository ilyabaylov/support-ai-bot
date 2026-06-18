"""Тесты на RAG-математику и базу знаний.

Сеть и Gemini тут не нужны — проверяем чистые функции и парсинг файла.
"""
from pathlib import Path

from app.rag.store import cosine, split_into_chunks

KB_FILE = Path(__file__).resolve().parents[1] / "knowledge_base" / "faq.md"


def test_cosine_identical():
    v = [1.0, 2.0, 3.0]
    assert abs(cosine(v, v) - 1.0) < 1e-9


def test_cosine_orthogonal():
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_empty_is_zero():
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_split_counts_sections():
    text = "## Цены\nманикюр 10000\n## Запись\nчерез whatsapp\n### Оплата\nkaspi"
    assert len(split_into_chunks(text)) == 3


def test_real_kb_splits_into_topics():
    # реальная база салона должна биться на осмысленное число разделов
    chunks = split_into_chunks(KB_FILE.read_text(encoding="utf-8"))
    assert len(chunks) >= 10
    assert any("Kaspi" in c for c in chunks)
