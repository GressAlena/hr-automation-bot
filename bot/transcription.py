from openai import OpenAI

from bot.config import OPENAI_API_KEY

_client = OpenAI(api_key=OPENAI_API_KEY)
_MODEL = "whisper-1"


def transcribe(file_bytes: bytes, filename: str = "voice.ogg") -> str:
    result = _client.audio.transcriptions.create(model=_MODEL, file=(filename, file_bytes))
    return result.text.strip()
