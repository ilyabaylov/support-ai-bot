"""Собирает векторный индекс из knowledge_base/faq.md.

Запуск:  python -m scripts.build_index
Нужен GEMINI_API_KEY — эмбеддинги считаются через Gemini.
"""
import asyncio

from app.config import load_config
from app.rag.indexer import build_index
from app.services.gemini import Gemini


async def main() -> None:
    cfg = load_config()
    if not cfg.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY не задан — без него эмбеддинги не посчитать.")

    gemini = Gemini(cfg.gemini_api_key, cfg.chat_model, cfg.embed_model)
    count = await build_index(gemini)
    print(f"Готово. Индекс собран: {count} кусочков базы знаний.")


if __name__ == "__main__":
    asyncio.run(main())
