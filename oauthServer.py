from flask import Flask, request, redirect
from threading import Thread
import asyncio
from aiogram import Bot
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import BOT_TOKEN
import requests

app = Flask(__name__)

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('oauthServer')

# Глобальные переменные
active_flows = {}
credentials_store = {}
bot_instance = None
loop = asyncio.new_event_loop()


def set_bot(bot: Bot):
    global bot_instance
    bot_instance = bot


def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }


def get_user_info_sync(credentials):
    """Синхронное получение информации о пользователе"""
    credentials_obj = Credentials(
        token=credentials['token'],
        refresh_token=credentials['refresh_token'],
        token_uri=credentials['token_uri'],
        client_id=credentials['client_id'],
        client_secret=credentials['client_secret'],
        scopes=credentials['scopes']
    )

    service = build('oauth2', 'v2', credentials=credentials_obj)
    return service.userinfo().get().execute()


@app.route('/callback')
def callback():
    """Обработка OAuth callback от Google"""
    try:
        # Получаем состояния
        state = request.args.get('state')
        code = request.args.get('code')

        # Лог колбека
        logger.info(f"Received callback: state={state}, code={code}")

        # Не получили статус или код
        if not state or not code:
            logger.error("Missing state or code parameters")
            return "Ошибка: отсутствует state или code", 400

        # Нет нужного состояния
        if state not in active_flows:
            logger.error(f"Invalid state parameter: {state}. Active states: {list(active_flows.keys())}")
            return f"Неверный state параметр: {state}", 400

        # получаем user_id
        user_id, flow = active_flows[state]

        # Обмен кода на токены
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Сохраняем учетные данные
        credentials_dict = credentials_to_dict(credentials)
        credentials_store[user_id] = credentials_dict

        # Уведомляем пользователя
        user_info = get_user_info_sync(credentials_dict)
        logger.info(f"User info retrieved: {user_info}")

        # Отправляем сообщение через бота (синхронно)
        if bot_instance:
            send_message_sync(user_id, f"✅ Авторизация успешна! Привет, {user_info['name']}!")
        else:
            logger.error("Bot instance not set")

        return redirect("https://telegram.me/giga_secretary_bot")

    except Exception as e:
        logger.exception("Exception in callback handler")
        error_msg = f"Ошибка авторизации: {str(e)}"

        # Попытка уведомить пользователя об ошибке
        try:
            if bot_instance:
                state = request.args.get('state')
                if state in active_flows:
                    user_id, _ = active_flows[state]
                    send_message_sync(user_id, error_msg)
        except Exception as inner_e:
            logger.error(f"Failed to send error message: {str(inner_e)}")

        return error_msg, 500


def send_message_sync(user_id, text):
    """Синхронная отправка сообщения через Telegram API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': user_id,
        'text': text,
        'parse_mode': 'HTML'
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Telegram API error: {str(e)}")
        return None


def run_flask_server():
    """Запускает Flask сервер"""
    app.run(port=8080, debug=False, use_reloader=False)


def start_flask_server():
    """Запускает Flask в отдельном потоке"""
    thread = Thread(target=run_flask_server)
    thread.daemon = True
    thread.start()

    logger.info("Flask server started on http://localhost:8080/callback")