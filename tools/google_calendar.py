from google.oauth2.credentials import Credentials
from oauthServer import credentials_store
import datetime
from pydantic import BaseModel, Field

from langchain_core.tools import tool


# Определяем модель для параметров инструмента
class ViewEventsInput(BaseModel):
    time_min: datetime.datetime = Field(description="Начало временного интервала")
    time_max: datetime.datetime = Field(description="Конец временного интервала")


# Создаем фабрику для инструмента с привязкой к user_id
def make_view_google_events_tool(user_id: int):
    @tool("view_google_events", args_schema=ViewEventsInput)
    async def view_google_events(time_min: datetime.datetime, time_max: datetime.datetime) -> list:
        """Получает события из Google Calendar для аутентифицированного пользователя"""
        from googleapiclient.discovery import build
        creds_data = credentials_store.get(user_id)

        if not creds_data:
            return "Ошибка: учетные данные не найдены. Пройдите аутентификацию."

        try:
            # Если хранится словарь - преобразуем в объект Credentials
            if isinstance(creds_data, dict):
                credentials = Credentials.from_authorized_user_info(creds_data)
            else:
                credentials = creds_data

            service = build("calendar", "v3", credentials=credentials)

            time_min_utc = time_min.astimezone(datetime.timezone.utc) if time_min.tzinfo else time_min.replace(
                tzinfo=datetime.timezone.utc)
            time_max_utc = time_max.astimezone(datetime.timezone.utc) if time_max.tzinfo else time_max.replace(
                tzinfo=datetime.timezone.utc)

            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min_utc.isoformat(),
                timeMax=time_max_utc.isoformat(),
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            # Форматирование ответа
            if isinstance(events, list):
                if not events:
                    response = "На этот период событий не найдено"
                else:
                    event_texts = []
                    for event in events:
                        start = event["start"].get("dateTime", event["start"].get("date"))
                        end = event["end"].get("dateTime", event["end"].get("date"))
                        summary = event.get("summary", "Без названия")
                        event_texts.append(f"• {summary} ({start} - {end})")
                    response = "\n".join(event_texts)
            else:
                response = events  # Готовое текстовое сообщение
            return response

        except Exception as e:
            return f"ERROR: Ошибка при получении событий."

    return view_google_events


class CreateEventInput(BaseModel):
    summary: str = Field(description="Название события")
    start_datetime: datetime.datetime = Field(description="Дата и время начала события")
    end_datetime: datetime.datetime = Field(description="Дата и время окончания события")
    description: str = Field(default="", description="Описание события")
    location: str = Field(default="", description="Место проведения")


def make_create_google_event_tool(user_id: int):
    @tool("create_google_event", args_schema=CreateEventInput)
    async def create_google_event(
            summary: str,
            start_datetime: datetime.datetime,
            end_datetime: datetime.datetime,
            description: str = "",
            location: str = ""
    ) -> str:
        """Создает новое событие в Google Calendar"""
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials

        creds_data = credentials_store.get(user_id)
        if not creds_data:
            return "Ошибка: учетные данные не найдены. Пройдите аутентификацию."

        try:
            if isinstance(creds_data, dict):
                credentials = Credentials.from_authorized_user_info(creds_data)
            else:
                credentials = creds_data

            service = build("calendar", "v3", credentials=credentials)

            # Форматирование времени для Google Calendar
            timezone = start_datetime.tzinfo.zone if start_datetime.tzinfo else "UTC"
            start = start_datetime.astimezone(datetime.timezone.utc).isoformat()
            end = end_datetime.astimezone(datetime.timezone.utc).isoformat()

            event = {
                'summary': summary,
                'description': description,
                'location': location,
                'start': {
                    'dateTime': start,
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end,
                    'timeZone': timezone,
                },
            }

            created_event = service.events().insert(
                calendarId='primary',
                body=event
            ).execute()

            return f"Событие создано: {created_event['htmlLink']}"

        except Exception as e:
            return f"ERROR: Ошибка при создании события: {str(e)}"

    return create_google_event


class DeleteEventInput(BaseModel):
    event_id: str = Field(description="ID события для удаления")


def make_delete_google_event_tool(user_id: int):
    @tool("delete_google_event", args_schema=DeleteEventInput)
    async def delete_google_event(event_id: str) -> str:
        """Удаляет событие из Google Calendar по его ID"""
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials

        creds_data = credentials_store.get(user_id)
        if not creds_data:
            return "Ошибка: учетные данные не найдены. Пройдите аутентификацию."

        try:
            if isinstance(creds_data, dict):
                credentials = Credentials.from_authorized_user_info(creds_data)
            else:
                credentials = creds_data

            service = build("calendar", "v3", credentials=credentials)

            service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()

            return f"Событие {event_id} успешно удалено"

        except Exception as e:
            return f"ERROR: Ошибка при удалении события: {str(e)}"

    return delete_google_event


class FindEventInput(BaseModel):
    summary: str = Field(description="Название события для поиска")
    date: datetime.date = Field(description="Дата события в формате YYYY-MM-DD")


def make_find_google_event_tool(user_id: int):
    @tool("find_google_event", args_schema=FindEventInput)
    async def find_google_event(summary: str, date: datetime.date) -> str:
        """Ищет событие в Google Calendar по названию и дате, возвращает его ID"""
        from googleapiclient.discovery import build

        creds_data = credentials_store.get(user_id)
        if not creds_data:
            return "Ошибка: учетные данные не найдены. Пройдите аутентификацию."

        try:
            # Преобразование учетных данных
            if isinstance(creds_data, dict):
                credentials = Credentials.from_authorized_user_info(creds_data)
            else:
                credentials = creds_data

            service = build("calendar", "v3", credentials=credentials)

            # Рассчитываем временной интервал для целого дня
            time_min = datetime.datetime(date.year, date.month, date.day, 0, 0, 0).isoformat() + 'Z'
            time_max = datetime.datetime(date.year, date.month, date.day, 23, 59, 59).isoformat() + 'Z'

            # Ищем события по названию в указанный день
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=5,
                singleEvents=True,
                orderBy='startTime',
                q=summary  # Поиск по названию
            ).execute()

            events = events_result.get('items', [])

            if not events:
                return f"Событие '{summary}' на {date} не найдено"

            # Фильтруем точные совпадения в названии
            exact_matches = [e for e in events if e.get('summary', '').lower() == summary.lower()]

            if not exact_matches:
                return f"Точного совпадения для '{summary}' не найдено. Найдены: {', '.join(e.get('summary') for e in events)}"

            if len(exact_matches) > 1:
                times = [e['start'].get('dateTime', e['start'].get('date')) for e in exact_matches]
                return f"Найдено несколько событий. Уточните время: {', '.join(times)}"

            return exact_matches[0]['id']  # Возвращаем ID события

        except Exception as e:
            return f"Ошибка при поиске: {str(e)}"

    return find_google_event


class UpdateEventInput(BaseModel):
    event_id: str = Field(description="ID события для обновления")
    summary: str = Field(default=None, description="Новое название события")
    start_datetime: datetime.datetime = Field(default=None, description="Новое время начала")
    end_datetime: datetime.datetime = Field(default=None, description="Новое время окончания")
    description: str = Field(default=None, description="Новое описание")
    location: str = Field(default=None, description="Новое место проведения")


def make_update_google_event_tool(user_id: int):
    @tool("update_google_event", args_schema=UpdateEventInput)
    async def update_google_event(
            event_id: str,
            summary: str = None,
            start_datetime: datetime.datetime = None,
            end_datetime: datetime.datetime = None,
            description: str = None,
            location: str = None
    ) -> str:
        """Обновляет существующее событие в Google Calendar"""
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials

        creds_data = credentials_store.get(user_id)
        if not creds_data:
            return "Ошибка: учетные данные не найдены. Пройдите аутентификацию."

        try:
            if isinstance(creds_data, dict):
                credentials = Credentials.from_authorized_user_info(creds_data)
            else:
                credentials = creds_data

            service = build("calendar", "v3", credentials=credentials)

            # Получаем текущую версию события
            event = service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()

            # Обновляем только переданные поля
            if summary is not None:
                event['summary'] = summary
            if description is not None:
                event['description'] = description
            if location is not None:
                event['location'] = location
            if start_datetime is not None:
                timezone = start_datetime.tzinfo.zone if start_datetime.tzinfo else "UTC"
                event['start'] = {
                    'dateTime': start_datetime.astimezone(datetime.timezone.utc).isoformat(),
                    'timeZone': timezone
                }
            if end_datetime is not None:
                timezone = end_datetime.tzinfo.zone if end_datetime.tzinfo else "UTC"
                event['end'] = {
                    'dateTime': end_datetime.astimezone(datetime.timezone.utc).isoformat(),
                    'timeZone': timezone
                }

            updated_event = service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event
            ).execute()

            return f"Событие обновлено: {updated_event['htmlLink']}"

        except Exception as e:
            return f"ERROR: Ошибка при обновлении события: {str(e)}"

    return update_google_event
