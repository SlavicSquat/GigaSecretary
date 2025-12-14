from aiogram import types, Router
from aiogram.filters import Command
from google_auth_oauthlib.flow import Flow
import datetime
from google.oauth2.credentials import Credentials
from oauthServer import active_flows, credentials_store
from config import CLIENT_SECRET_FILE, SCOPES, REDIRECT_URI
import uuid


command_router = Router()


async def get_user_info(credentials):
    """Получаем информацию о пользователе Google"""
    from googleapiclient.discovery import build
    service = build('oauth2', 'v2', credentials=credentials)
    user_info = service.userinfo().get().execute()
    return user_info


async def get_events(credentials):
    """Получаем события"""
    from googleapiclient.discovery import build
    service = build("calendar", "v3", credentials=credentials)

    # Call the Calendar API
    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    print("Getting the upcoming 10 events")
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    return events


@command_router.message(Command("start"))
async def handle_start(message: types.Message):
    await message.answer("Привет! Для авторизации используй /login")


@command_router.message(Command("login"))
async def handle_login(message: types.Message):
    user_id = message.from_user.id

    try:
        # Создаем OAuth поток
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )

        # Генерируем уникальный state для защиты от CSRF
        state = str(uuid.uuid4())

        # Генерируем URL авторизации
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            state=state
        )

        # Сохраняем flow для последующего использования
        active_flows[state] = (user_id, flow)

        # Отправляем кнопку с ссылкой
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔑 Авторизоваться через Google", url=auth_url)]
        ])

        await message.answer(
            "Нажмите кнопку для авторизации:\n"
            "1. Разрешите доступ вашему аккаунту\n"
            "2. После авторизации вы будете перенаправлены обратно в Telegram\n"
            "3. Бот уведомит вас об успешной авторизации",
            reply_markup=keyboard
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@command_router.message(Command("events"))
async def handle_events(message: types.Message):
    """Вывод 10 следующих событий"""
    user_id = message.from_user.id

    if user_id not in credentials_store:
        await message.answer("❌ Сначала авторизуйтесь через /login")
        return

    try:
        # Восстанавливаем credentials
        creds_data = credentials_store[user_id]
        credentials = Credentials(
            token=creds_data['token'],
            refresh_token=creds_data['refresh_token'],
            token_uri=creds_data['token_uri'],
            client_id=creds_data['client_id'],
            client_secret=creds_data['client_secret'],
            scopes=creds_data['scopes']
        )

        # Получаем события
        events = await get_events(credentials)
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            await message.answer(f"Вот твой ивент: {start} {event["summary"]}")

    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {str(e)}\nПопробуйте снова: /login")
