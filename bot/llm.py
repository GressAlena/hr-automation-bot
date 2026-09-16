import json
import re

from openai import OpenAI

from bot.config import OPENAI_API_KEY

_client = OpenAI(api_key=OPENAI_API_KEY)

_MODEL = "gpt-4o-mini"

_SYSTEM_PROMPT = """\
Ты — опытный технический рекрутер-скринер. Тебе дают текст вакансии и текст резюме кандидата.
Сравни резюме с требованиями вакансии и оцени соответствие.

Ответь СТРОГО в виде JSON без какого-либо текста до или после, по такой схеме:
{
  "score": <целое число от 0 до 100, насколько кандидат подходит под вакансию>,
  "summary": "<2-3 предложения с общим выводом>",
  "strengths": ["<сильная сторона 1>", "<сильная сторона 2>", ...],
  "gaps": ["<пробел/несоответствие 1>", "<пробел/несоответствие 2>", ...],
  "recommendation": "<короткая рекомендация: пригласить на собеседование / рассмотреть с оговорками / отказать>"
}
"""

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class ScoringError(Exception):
    pass


def score_resume(resume_text: str, vacancy_title: str, vacancy_description: str) -> dict:
    user_prompt = (
        f"Вакансия: {vacancy_title}\n\n"
        f"Описание вакансии:\n{vacancy_description}\n\n"
        f"Резюме кандидата:\n{resume_text}"
    )

    response = _client.chat.completions.create(
        model=_MODEL,
        max_tokens=1024,
        temperature=0,
        seed=42,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_text = response.choices[0].message.content or ""
    return _parse_json_response(raw_text)


def _parse_json_response(raw_text: str) -> dict:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        match = _JSON_BLOCK_RE.search(raw_text)
        if not match:
            raise ScoringError(f"Модель вернула ответ без JSON: {raw_text[:500]}")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ScoringError(f"Не удалось разобрать JSON от модели: {exc}") from exc

    required = {"score", "summary", "strengths", "gaps", "recommendation"}
    missing = required - data.keys()
    if missing:
        raise ScoringError(f"В ответе модели не хватает полей: {missing}")

    return data
