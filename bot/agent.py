import logging
import uuid

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from bot import db
from bot import llm as scoring
from bot.config import OPENAI_API_KEY

_MODEL = "gpt-4o-mini"
_MAX_HISTORY_MESSAGES = 20

_model = ChatOpenAI(model=_MODEL, api_key=OPENAI_API_KEY, temperature=0)
_logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Ты — HR-ассистент в Telegram-боте компании. Помогаешь вести вакансии и кандидатов.

Правила:
- Отвечай по-русски, простым текстом без Markdown/HTML-разметки (никаких **, ##, \
обратных кавычек) — сообщение уходит в Telegram как обычный текст.
- Вакансии и кандидаты у тебя есть только через инструменты — ничего не выдумывай \
про них от себя. Если пользователь называет вакансию или кандидата словами, а не \
id, сначала найди id через search_vacancies/list_vacancies или search_candidates, \
и только потом вызывай инструменты, которым нужен id.
- Если находится несколько подходящих вакансий/кандидатов — покажи варианты и \
попроси уточнить, не гадай.
- Резюме кандидата пользователь присылает файлом, текстом или голосовым; когда оно \
есть, но ещё не оценено, у тебя будет инструмент score_pending_resume — сначала \
выясни, к какой вакансии оно относится (по контексту переписки или явным вопросом), \
потом вызови этот инструмент.
- Когда пользователь присылает файл, ты не видишь его целиком — только превью в \
сообщении. Файл может быть РЕЗЮМЕ КАНДИДАТА, ОПИСАНИЕМ ВАКАНСИИ или чем-то другим — \
определи по превью и контексту диалога, не считай по умолчанию, что это резюме. \
Для резюме используй score_pending_resume. Для описания вакансии — ОБЯЗАТЕЛЬНО \
create_vacancy_from_pending (никогда не create_vacancy!) — ты видел только превью, \
а не весь файл, поэтому не можешь сам написать полное description: create_vacancy_\
from_pending сам возьмёт полный исходный текст файла. create_vacancy используй, \
только когда пользователь описал вакансию прямо в сообщении (не файлом) и весь \
текст описания у тебя перед глазами. Никогда не оценивай текст вакансии как резюме \
кандидата и не создавай вакансию из резюме.
- Перед тем как создать вакансию (create_vacancy или create_vacancy_from_pending), \
ОБЯЗАТЕЛЬНО вызови search_vacancies с предполагаемым названием, чтобы проверить, \
нет ли уже такой же или очень похожей открытой вакансии. Если похожая вакансия уже \
есть — не создавай новую молча: скажи об этом пользователю и спроси, создать ли \
всё-таки ещё одну (например, если это отдельная позиция с тем же названием), или \
он имел в виду уже существующую. Не создавай вакансии-дубликаты по умолчанию.
- Статус кандидата (new/invited/on_hold/rejected) меняй через set_candidate_status.
- Никогда не отвечай обещаниями вроде «сейчас оценю», «одну минуту», «уже делаю» — \
у тебя нет фонового выполнения, если ты не вызвал инструмент прямо сейчас, он не \
выполнится, а пользователь получит только пустое обещание и будет ждать зря. Либо \
вызови нужный инструмент в этом же ответе и сообщи реальный результат, либо, если \
не хватает данных (например, не ясно, к какой вакансии отнести резюме), задай \
конкретный уточняющий вопрос.
- Никогда не утверждай, что кандидат/вакансия уже существует, уже оценены или что-\
то с ними уже сделано, если ты не проверил это инструментом (search_candidates, \
get_candidate, list_candidates_for_vacancy и т.п.) в этом же ответе. Не полагайся \
на память о более ранних сообщениях переписки для таких утверждений — переписка \
могла обрезаться, а твоя память о ней может быть неточной. Если сомневаешься — \
сначала проверь инструментом, потом отвечай.
- id вакансии и кандидата — это всегда UUID, возвращённый инструментами поиска/списка. \
Никогда не подставляй в качестве id имя, название или что-то придуманное — если у \
тебя нет id из результата инструмента, сначала вызови list/search. Если id уже \
явно указан в сообщении пользователя или в процитированном сообщении (например, \
там написано «id=...»), используй его напрямую, не переспрашивай.
- Сообщения могут начинаться со служебных пометок в квадратных скобках — это не \
слова пользователя, а контекст: «[Переслано...]» значит текст ниже прислали не \
как команду, а как материал (резюме, описание вакансии и т.п.) — разберись, что \
это, и предложи подходящее действие или уточни, что с этим сделать; «[В ответ на \
сообщение]: ...» показывает, на какое сообщение отвечает пользователь — используй \
это как дополнительный контекст (там может быть id вакансии/кандидата).
- Голосовые сообщения приходят уже расшифрованными в текст — обращайся с ними как \
с обычным сообщением, при необходимости учитывая, что распознавание речи иногда \
ошибается (спроси, если что-то не имеет смысла).
- Будь краток и по делу, как коллега, а не как формальный бот.
- Не добавляй в конце ответа дежурные фразы вроде «если нужно что-то ещё, дайте \
знать», «обращайтесь, если будут вопросы», «дайте знать, что делать дальше» и \
подобные — заканчивай ответ на сути дела, без формальной концовки. Задавай вопрос \
в конце, только если он конкретный и по существу (например, реально нужно уточнить \
вакансию или статус), а не как общая вежливая фраза.
"""

_STATUS_VALUES = {"new", "invited", "on_hold", "rejected"}


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _not_uuid_hint(value: str) -> str:
    return (
        f"«{value}» не похоже на id (id — это UUID). Сначала найди нужную запись "
        f"через list_vacancies/search_vacancies или search_candidates и возьми id из результата."
    )


def _history_to_messages(history: list[dict]) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for item in history:
        if item.get("role") == "human":
            messages.append(HumanMessage(content=item["content"]))
        else:
            messages.append(AIMessage(content=item["content"]))
    return messages


def _format_vacancy_line(v: dict) -> str:
    return f"id={v['id']} | {v['title']}"


def _format_candidate_line(c: dict) -> str:
    vacancy_title = (c.get("vacancies") or {}).get("title", "?")
    return (
        f"id={c['id']} | {c['file_name']} | вакансия: {vacancy_title} | "
        f"балл: {c['score']} | статус: {c['status']}"
    )


def _build_tools(chat_id: int, session_state: dict) -> list:
    @tool
    def create_vacancy(title: str, description: str) -> str:
        """Создать новую вакансию из текста, который пользователь написал прямо в сообщении (не файлом). Аргументы: title — короткое название, description — полный текст вакансии (требования, обязанности, условия). Если вакансия пришла файлом — используй create_vacancy_from_pending, а не этот инструмент, иначе описание будет неполным."""
        vacancy = db.create_vacancy(title, description, chat_id)
        return f"Вакансия создана. id={vacancy['id']}, название: {vacancy['title']}"

    @tool
    def list_vacancies() -> str:
        """Показать все открытые вакансии (id и название)."""
        vacancies = db.list_open_vacancies()
        if not vacancies:
            return "Открытых вакансий пока нет."
        return "\n".join(_format_vacancy_line(v) for v in vacancies)

    @tool
    def search_vacancies(query: str) -> str:
        """Найти открытые вакансии по части названия."""
        vacancies = db.search_vacancies(query)
        if not vacancies:
            return "Ничего не найдено по этому запросу."
        return "\n".join(_format_vacancy_line(v) for v in vacancies)

    @tool
    def get_vacancy(vacancy_id: str) -> str:
        """Получить полное описание вакансии по её id."""
        if not _is_uuid(vacancy_id):
            return _not_uuid_hint(vacancy_id)
        vacancy = db.get_vacancy(vacancy_id)
        if not vacancy:
            return "Вакансия с таким id не найдена."
        return (
            f"id={vacancy['id']}\nНазвание: {vacancy['title']}\n"
            f"Статус: {vacancy['status']}\nОписание:\n{vacancy['description']}"
        )

    @tool
    def list_candidates_for_vacancy(vacancy_id: str) -> str:
        """Список кандидатов по вакансии (по id вакансии), отсортированный по баллу от большего к меньшему."""
        if not _is_uuid(vacancy_id):
            return _not_uuid_hint(vacancy_id)
        candidates = db.list_candidates(vacancy_id)
        if not candidates:
            return "По этой вакансии кандидатов пока нет."
        lines = [
            f"id={c['id']} | {c['file_name']} | балл: {c['score']} | статус: {c['status']}"
            for c in candidates
        ]
        return "\n".join(lines)

    @tool
    def search_candidates(query: str) -> str:
        """Найти кандидатов по части имени файла резюме (обычно там имя/фамилия кандидата)."""
        candidates = db.search_candidates(query)
        if not candidates:
            return "Ничего не найдено по этому запросу."
        return "\n".join(_format_candidate_line(c) for c in candidates)

    @tool
    def get_candidate(candidate_id: str) -> str:
        """Полная информация о кандидате по его id: балл, резюме анализа, сильные стороны, пробелы, рекомендация, статус."""
        if not _is_uuid(candidate_id):
            return _not_uuid_hint(candidate_id)
        candidate = db.get_candidate(candidate_id)
        if not candidate:
            return "Кандидат с таким id не найден."
        return (
            f"id={candidate['id']}\nФайл: {candidate['file_name']}\n"
            f"Балл: {candidate['score']}/100\nСтатус: {candidate['status']}\n"
            f"Итог: {candidate['summary']}\nСильные стороны:\n{candidate['strengths']}\n"
            f"Пробелы:\n{candidate['gaps']}\nРекомендация: {candidate['recommendation']}"
        )

    @tool
    def set_candidate_status(candidate_id: str, status: str) -> str:
        """Изменить статус кандидата. status — одно из: new, invited, on_hold, rejected."""
        if not _is_uuid(candidate_id):
            return _not_uuid_hint(candidate_id)
        if status not in _STATUS_VALUES:
            return f"Некорректный статус «{status}». Допустимые значения: {', '.join(sorted(_STATUS_VALUES))}."
        db.update_candidate_status(candidate_id, status)
        return "Статус обновлён."

    @tool
    def score_pending_resume(vacancy_id: str) -> str:
        """Оценить последний загруженный, но ещё не обработанный текст как резюме кандидата на соответствие вакансии (по id вакансии). Используй, только если загруженное — это резюме, а не описание вакансии или что-то другое."""
        if not _is_uuid(vacancy_id):
            return _not_uuid_hint(vacancy_id)

        pending = session_state.get("pending_upload")
        if not pending:
            return "Нет загруженного текста для оценки. Попроси прислать файл резюме, текст или голосовое."

        vacancy = db.get_vacancy(vacancy_id)
        if not vacancy:
            return "Вакансия с таким id не найдена."

        analysis = scoring.score_resume(pending["text"], vacancy["title"], vacancy["description"])
        strengths = "\n".join(f"- {s}" for s in analysis["strengths"]) or "-"
        gaps = "\n".join(f"- {g}" for g in analysis["gaps"]) or "-"

        candidate = db.create_candidate(
            vacancy_id=vacancy_id,
            file_name=pending["file_name"],
            resume_text=pending["text"],
            score=analysis["score"],
            summary=analysis["summary"],
            strengths=strengths,
            gaps=gaps,
            recommendation=analysis["recommendation"],
            uploaded_by=chat_id,
        )

        session_state["pending_upload"] = None
        session_state["new_candidate_id"] = candidate["id"]

        return (
            f"Кандидат оценён (id={candidate['id']}).\n"
            f"Балл: {analysis['score']}/100\n"
            f"Итог: {analysis['summary']}\n"
            f"Сильные стороны:\n{strengths}\n"
            f"Пробелы:\n{gaps}\n"
            f"Рекомендация: {analysis['recommendation']}"
        )

    @tool
    def create_vacancy_from_pending(title: str) -> str:
        """Создать вакансию из последнего загруженного, но ещё не обработанного текста, когда он оказался описанием вакансии, а не резюме. title — короткое название вакансии."""
        pending = session_state.get("pending_upload")
        if not pending:
            return "Нет загруженного текста для создания вакансии из него."

        vacancy = db.create_vacancy(title, pending["text"], chat_id)
        session_state["pending_upload"] = None
        return f"Вакансия создана. id={vacancy['id']}, название: {vacancy['title']}"

    return [
        create_vacancy,
        list_vacancies,
        search_vacancies,
        get_vacancy,
        list_candidates_for_vacancy,
        search_candidates,
        get_candidate,
        set_candidate_status,
        score_pending_resume,
        create_vacancy_from_pending,
    ]


_UNSET = object()


def _run(chat_id: int, user_input: str, pending_upload_override=_UNSET) -> dict:
    session = db.get_session(chat_id)
    pending_upload = session["pending_upload"] if pending_upload_override is _UNSET else pending_upload_override

    session_state = {"pending_upload": pending_upload, "new_candidate_id": None}
    tools = _build_tools(chat_id, session_state)
    graph = create_agent(_model, tools, system_prompt=_SYSTEM_PROMPT)

    chat_history = _history_to_messages(session["history"])[-_MAX_HISTORY_MESSAGES:]
    messages = chat_history + [HumanMessage(content=user_input)]
    try:
        result = graph.invoke({"messages": messages})
        output = result["messages"][-1].content
    except Exception:
        _logger.exception("Agent run failed for chat_id=%s", chat_id)
        return {"text": "Произошла техническая ошибка, попробуйте переформулировать запрос.", "new_candidate_id": None}

    new_history = session["history"] + [
        {"role": "human", "content": user_input},
        {"role": "ai", "content": output},
    ]
    new_history = new_history[-_MAX_HISTORY_MESSAGES:]

    db.save_session(chat_id, new_history, session_state["pending_upload"])

    return {"text": output, "new_candidate_id": session_state["new_candidate_id"]}


def handle_text(chat_id: int, prompt: str, pending_candidate_text: str | None = None, pending_file_name: str = "текст из чата") -> dict:
    pending_upload_override = _UNSET
    if pending_candidate_text:
        pending_upload_override = {"file_name": pending_file_name, "text": pending_candidate_text}
    return _run(chat_id, prompt, pending_upload_override=pending_upload_override)


_PREVIEW_CHARS = 800


def handle_document(chat_id: int, file_name: str, text: str, extra_context: str | None = None) -> dict:
    preview = text[:_PREVIEW_CHARS]
    truncated_note = " (обрезано для превью)" if len(text) > _PREVIEW_CHARS else ""
    prompt = (
        f"Пользователь прислал файл «{file_name}». Вот начало его текста{truncated_note}:\n"
        f"---\n{preview}\n---\n\n"
        "Определи, что это, и сделай подходящее:\n"
        "- если это резюме кандидата — определи вакансию по контексту диалога (или спроси) "
        "и оцени через score_pending_resume;\n"
        "- если это описание вакансии — СНАЧАЛА вызови search_vacancies с предполагаемым "
        "названием и проверь, нет ли уже такой же/похожей открытой вакансии; если похожая "
        "уже есть — не создавай новую, а сообщи об этом и спроси, что делать; только если "
        "дублей нет — создай через create_vacancy_from_pending, подобрав короткое название;\n"
        "- если что-то другое или непонятно — спроси, что с этим сделать.\n\n"
        "Ответь без вступлений и без дежурных фраз в конце (никаких «если нужно что-то ещё, "
        "дайте знать» и подобного) — только суть."
    )
    if extra_context:
        prompt = f"{extra_context}\n{prompt}"
    return _run(chat_id, prompt, pending_upload_override={"file_name": file_name, "text": text})


def reset(chat_id: int) -> None:
    db.save_session(chat_id, [], None)
