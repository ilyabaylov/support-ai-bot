"""Память диалога по каждому пользователю.

Держим последние несколько реплик в памяти — без этого бот отвечал бы каждый
раз «с чистого листа» и не понимал контекст («а сколько тогда в субботу?»).

Храним в памяти процесса: просто и быстро. При перезапуске бота история обнуляется —
для салонного бота этого достаточно (см. раздел Ограничения в README).
Роли — в формате Gemini: "user" и "model".
"""
from __future__ import annotations

from collections import defaultdict, deque

# сколько реплик помним (6 пар «вопрос–ответ») — хватает для контекста, но не раздувает промпт
MAX_MESSAGES = 12

_store: dict[int, deque[tuple[str, str]]] = defaultdict(lambda: deque(maxlen=MAX_MESSAGES))


def history(user_id: int) -> list[tuple[str, str]]:
    """История реплик пользователя в хронологическом порядке."""
    return list(_store[user_id])


def remember(user_id: int, role: str, text: str) -> None:
    if text:
        _store[user_id].append((role, text))


def reset(user_id: int) -> None:
    """Сброс при /start — начинаем разговор заново."""
    _store.pop(user_id, None)
