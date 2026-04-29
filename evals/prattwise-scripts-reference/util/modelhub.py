import requests
import json
from os import getenv, environ
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta


load_dotenv()


class ModelHubToken:
    token: str
    expired_date: datetime | None = None
    file: Path = Path("config", "model_hub_secret.json")

    @classmethod
    def get(cls):
        cls.load()
        if cls.is_expired():
            return cls._refresh_modelhub_token()
        return cls.token

    @classmethod
    def is_expired(cls):
        if cls.expired_date:
            return cls.expired_date < datetime.now()
        return True

    @staticmethod
    def save(token: str, expired_date: datetime):
        with open(ModelHubToken.file, "w+") as file:
            json.dump(
                {"token": token, "expired_date": expired_date.isoformat()},
                file,
                indent=4,
            )

    @classmethod
    def load(cls):
        if not cls.file.parent.exists():
            cls.file.parent.mkdir(parents=True)
            return
        if not cls.file.exists():
            return
        with open(cls.file, "r") as file:
            try:
                data = json.load(file)
                cls.token = data["token"]
                cls.expired_date = datetime.fromisoformat(data["expired_date"])
            except Exception:
                return

    @classmethod
    def _refresh_modelhub_token(cls):
        print("Get new token.")
        url = getenv("MODELHUB_TOKEN_ENDPOINT", None)
        if url is None:
            raise RuntimeError("MODELHUB_TOKEN_ENDPOINT is not set.")
        payload = {
            "client_id": environ.get("MODELHUB_TOKEN_CLIENT_ID"),
            "client_secret": getenv("MODELHUB_TOKEN_CLIENT_SECRET"),
            "scope": getenv("MODELHUB_TOKEN_SCOPE"),
            "grant_type": "client_credentials",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(url=url, data=payload, headers=headers, verify=False)
        token = response.json()["access_token"]
        expired_date = datetime.now() + timedelta(minutes=50)
        cls.token = token
        cls.expired_date = expired_date
        ModelHubToken.save(token, expired_date)
        return token


SESSION = None


def get_token():
    global SESSION
    if SESSION is None:
        SESSION = requests.Session()
    if not ModelHubToken.is_expired():
        return ModelHubToken.token
    return ModelHubToken.get()


if __name__ == "__main__":
    token = get_token()
    print(f"TOKEN: {token}")
