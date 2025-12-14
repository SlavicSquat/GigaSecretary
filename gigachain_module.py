from langchain_gigachat import GigaChat
from giga_api_config import *


def get_model():
    model = GigaChat(
        credentials=CLIENT_ID,
        model="GigaChat-2-Max",
        verify_ssl_certs=False,
        scope=SCOPE,
        profanity_check=False,
        temperature=0.1
    )
    return model
