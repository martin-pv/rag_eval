from requests import Session
from dotenv import load_dotenv
from os import environ

from util.modelhub import get_token

import json


load_dotenv()


class AzureOpenAI:
    SESSION: Session | None = None
    URL: str
    HEADERS: dict
    OPENAI_API_LLM_KEY: str

    @classmethod
    def setup(cls) -> None:
        OPENAI_API_LLM_ENDPOINT = environ.get("OPENAI_API_LLM_ENDPOINT")
        OPENAI_API_LLM_DEPLOYMENT = environ.get("OPENAI_API_LLM_DEPLOYMENT")
        OPENAI_API_LLM_VERSION = environ.get("OPENAI_API_LLM_VERSION")
        cls.URL = (
            f"{OPENAI_API_LLM_ENDPOINT}/openai/deployments/"
            f"{OPENAI_API_LLM_DEPLOYMENT}/chat/completions?api-version={OPENAI_API_LLM_VERSION}"
        )
        cls.OPENAI_API_LLM_KEY = environ.get("OPENAI_API_LLM_KEY", "")
        cls._update_headers()
        cls.SESSION = Session()

    @classmethod
    def get(cls):
        if not cls.SESSION:
            cls.setup()
        cls._update_headers()
        response = cls.SESSION.get(url=cls.URL, headers=cls.HEADERS)
        if response.ok:
            return response
        raise RuntimeError(f"Error: {response.text}")

    @classmethod
    def post(cls, data: dict):
        if not cls.SESSION:
            cls.setup()

        if len(data["messages"]) < 1:
            raise RuntimeError("messages must contain at least 1 entry")

        cls._update_headers()
        if cls.SESSION is None:
            raise RuntimeError("SESSION cannot be none")

        response = cls.SESSION.post(
            url=cls.URL,
            headers=cls.HEADERS,
            json=data,
        )
        if response.ok:
            return response
        raise RuntimeError(f"Status: {response.status_code}\n{response.text}")

    @classmethod
    def _update_headers(cls):
        MODEL_HUB_TOKEN = get_token()
        cls.HEADERS = {
            "Content-Type": "application/json",
            "api-key": f"{cls.OPENAI_API_LLM_KEY}",
            "Ocp-Apim-Subscription-Key": f"{cls.OPENAI_API_LLM_KEY}",
            "Authorization": f"Bearer {MODEL_HUB_TOKEN}",
        }
