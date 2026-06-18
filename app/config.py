"""Конфиг приложения — всё читаем из переменных окружения (.env)."""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    gemini_api_key: str
    admin_ids: set[int]
    operator_chat_id: int | None
    chat_model: str
    embed_model: str
    sim_threshold: float
    top_k: int

    @property
    def operator_target(self) -> int | None:
        """Куда слать обращения. Если отдельный чат не задан — первому админу."""
        if self.operator_chat_id:
            return self.operator_chat_id
        return next(iter(self.admin_ids), None)


def _parse_ids(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part:
            ids.add(int(part))
    return ids


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        # без токена смысла стартовать нет — сразу честно падаем
        raise RuntimeError("BOT_TOKEN не задан. Скопируй .env.example в .env и впиши токен.")

    operator = os.getenv("OPERATOR_CHAT_ID", "").strip()

    return Config(
        bot_token=token,
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        admin_ids=_parse_ids(os.getenv("ADMIN_IDS", "")),
        operator_chat_id=int(operator) if operator else None,
        chat_model=os.getenv("CHAT_MODEL", "gemini-2.0-flash"),
        embed_model=os.getenv("EMBED_MODEL", "text-embedding-004"),
        sim_threshold=float(os.getenv("SIM_THRESHOLD", "0.62")),
        top_k=int(os.getenv("TOP_K", "4")),
    )
