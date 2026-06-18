"""Тонкая обёртка над Gemini: эмбеддинги, диалог со стримингом и расшифровка голоса.

Весь доступ к модели держим в одном месте — так проще поменять модель
или вообще провайдера, не трогая хендлеры.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
import httpx

from google import genai
from google.genai import types


class Gemini:
    def __init__(self, api_key: str, chat_model: str, embed_model: str) -> None:
        # один клиент на всё приложение, используем httpx вместо aiohttp во избежание ошибки readline
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                httpx_async_client=httpx.AsyncClient()
            )
        )
        self._chat_model = chat_model
        self._embed_model = embed_model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # эмбеддим пачкой — так дешевле и быстрее, чем по одному
        res = await self._client.aio.models.embed_content(
            model=self._embed_model,
            contents=texts,
        )
        return [e.values for e in res.embeddings]

    async def embed_one(self, text: str) -> list[float]:
        vectors = await self.embed([text])
        return vectors[0]

    async def transcribe_voice(self, audio: bytes, mime: str = "audio/ogg") -> str:
        # голосовые в телеге приходят в ogg/opus, Gemini читает их напрямую
        res = await self._client.aio.models.generate_content(
            model=self._chat_model,
            contents=[
                "Расшифруй это голосовое сообщение в текст. Верни только текст, без комментариев.",
                types.Part.from_bytes(data=audio, mime_type=mime),
            ],
        )
        return (res.text or "").strip()

    async def chat_stream(
        self,
        system_prompt: str,
        history: list[tuple[str, str]],
        user_message: str,
    ) -> AsyncIterator[str]:
        """Диалог с памятью: передаём всю историю + новый вопрос, стримим ответ.

        system_prompt задаёт личность и кладёт факты из базы; история — предыдущие реплики.
        """
        contents: list[types.Content] = []
        for role, text in history:
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=text)])
            )
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
        )

        stream = await self._client.aio.models.generate_content_stream(
            model=self._chat_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                # живой администратор, но без фантазий про цены — средняя температура
                temperature=0.6,
            ),
        )
        async for chunk in stream:
            if chunk.text:
                yield chunk.text
