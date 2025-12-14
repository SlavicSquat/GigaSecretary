from aiogram import types, Router
from dotenv import find_dotenv, load_dotenv
import os
import json
from db import bot

from langchain_gigachat import GigaChat

from tools.google_calendar import (make_view_google_events_tool,
                                   make_create_google_event_tool,
                                   make_delete_google_event_tool,
                                   make_find_google_event_tool,
                                   make_update_google_event_tool)

from LLMAgent import LLMAgent
from STT import convert_ogg_to_wav, recognize_speech


text_router = Router()

load_dotenv(find_dotenv())

model = GigaChat(
        model="GigaChat-2",
        verify_ssl_certs=False
    )


async def get_ai_response(message, user_id):

    google_view_events_tool = make_view_google_events_tool(user_id)
    google_find_events_tool = make_find_google_event_tool(user_id)
    google_create_events_tool = make_create_google_event_tool(user_id)
    google_delete_events_tool = make_delete_google_event_tool(user_id)
    google_update_events_tool = make_update_google_event_tool(user_id)

    tools = [google_view_events_tool,
             google_find_events_tool,
             google_create_events_tool,
             google_delete_events_tool,
             google_update_events_tool]

    # Делаем агента
    agent = LLMAgent(
        model=model,
        tools=tools,
        user_id=user_id
    )

    # Получаем ответ
    return await agent.ainvoke(message)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)


async def speech_to_text(message: types.Message):

    answer = ''

    """Обработчик голосовых сообщений"""
    voice = message.voice
    file_id = voice.file_id

    # Создаем пути с полными именами
    ogg_path = os.path.join(TEMP_DIR, f"{file_id}.ogg")
    wav_path = os.path.join(TEMP_DIR, f"{file_id}.wav")

    try:
        # Скачивание файла
        file = await bot.get_file(file_id)
        await bot.download(file, destination=ogg_path)

        # Конвертация
        await convert_ogg_to_wav(ogg_path, wav_path)

        # Распознавание
        text = await recognize_speech(wav_path)
        if text.strip():
            answer = text
        else:
            answer = "Не удалось распознать речь"
    except Exception as e:
        answer = str(e)
    finally:
        # Безопасное удаление файлов
        for path in [ogg_path, wav_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Ошибка удаления файла {path}: {e}")

    return answer


@text_router.message()
async def handle_text(message: types.Message):
    request = ''
    if message.content_type == types.ContentType.VOICE:
        request = await speech_to_text(message)
    else:
        request = message.text

    await message.answer(await get_ai_response(request, message.from_user.id))
