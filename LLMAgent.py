import datetime

from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage


class LLMAgent:
    def __init__(self, model, tools, user_id):
        self._model = model.bind_functions(tools)
        self._agent = create_react_agent(
            model,
            tools=tools,
            checkpointer=MemorySaver())
        self._user_id = user_id
        self._config: RunnableConfig = {
            "configurable": {"thread_id": self._user_id}}

    async def ainvoke(self, message):
        today = datetime.datetime.now()

        system_prompt = (
            f"Текущая дата: {today}. Ты - ассистент для работы с Google Calendar. "
            "Доступные инструменты:"
            "1. view_google_events - для просмотра событий (аргументы: time_min, time_max)"
            "2. create_google_event - для создания событий (аргументы: summary, start_datetime, end_datetime)"
            "3. update_google_event - для обновления событий (аргументы: event_id, summary, start_datetime и др.)"
            "4. delete_google_event - для удаления событий (аргументы: event_id)"
            "5. find_google_event - для получения id события (аргументы: summary, date)"
            "Все даты должны быть в формате ISO 8601."
            "Отвечай кратко, используй инструменты для выполнения действий."
        )

        # Формируем сообщения для агента
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ]

        # Вызываем агента
        agent_response = await self._agent.ainvoke(
            {"messages": messages},
            config=self._config
        )

        return agent_response['messages'][-1].content

