import os
import sys
import asyncio
from dotenv import load_dotenv

# Добавляем корневую директорию проекта в пути поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import load_config
from app.rag.store import KnowledgeBase
from app.services.gemini import Gemini
import app.content as content

async def main():
    print("Загрузка конфигурации и базы знаний...")
    load_dotenv()
    try:
        cfg = load_config()
    except Exception as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        return

    try:
        kbase = KnowledgeBase.load()
    except Exception as e:
        print(f"Не удалось загрузить базу знаний. Сначала соберите индекс: python -m scripts.build_index")
        return

    gemini = Gemini(cfg.gemini_api_key, cfg.chat_model, cfg.embed_model)
    history = []
    
    print("\n==================================================")
    print("Бот готов к общению в консоли!")
    print("Напишите 'выход' или 'exit' для завершения диалога.")
    print("==================================================\n")
    
    # Приветствие
    print(f"Бот (Аружан): {content.WELCOME}\n")
    
    while True:
        try:
            question = input("Вы: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nВыход из чата.")
            break
            
        if not question:
            continue
            
        if question.lower() in ["выход", "exit", "quit", "q"]:
            print("Выход из чата.")
            break
            
        # 1. Поиск в RAG
        best_score = 0.0
        context = ""
        try:
            q_vec = await gemini.embed_one(question)
            found = kbase.search(q_vec, cfg.top_k)
            best_score = found[0][0] if found else 0.0
            context = "\n\n---\n\n".join(chunk for _, chunk in found)
        except Exception as e:
            print(f"(Ошибка поиска в RAG: {e})")

        if not context:
            context = "(по этому вопросу в базе нет прямых данных)"
        if best_score < cfg.sim_threshold:
            context = (
                "⚠️ По этому вопросу в базе нет точных данных — отвечай общими словами, "
                "не выдумывай цифры, при необходимости предложи уточнить у мастера.\n\n" + context
            )

        system = (
            "{persona}\n\n"
            "ЧТО МЫ ЗНАЕМ (база салона, твой источник правды):\n{context}"
        ).format(persona=content.PERSONA, context=context)

        print("Бот (Аружан): ", end="", flush=True)
        
        buffer = ""
        try:
            async for piece in gemini.chat_stream(system, history, question):
                buffer += piece
                print(piece, end="", flush=True)
            print("\n")
        except Exception as e:
            print(f"\nОшибка обращения к Gemini API: {e}\n")
            continue
            
        # Запоминаем в историю
        raw = buffer.strip()
        needs_human = "[[HANDOFF]]" in raw
        answer = raw.replace("[[HANDOFF]]", "").strip()
        if not answer:
            answer = "Уточните, пожалуйста, чуть подробнее — и я помогу 🙌"
            
        history.append(("user", question))
        history.append(("model", answer))
        
        if needs_human:
            print("🔔 [Система: Передано администратору (HANDOFF triggered)]\n")

if __name__ == "__main__":
    asyncio.run(main())
