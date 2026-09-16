from supabase import Client, create_client

from bot.config import SUPABASE_SERVICE_KEY, SUPABASE_URL

_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def create_vacancy(title: str, description: str, created_by: int) -> dict:
    result = (
        _client.table("vacancies")
        .insert({"title": title, "description": description, "created_by": created_by})
        .execute()
    )
    return result.data[0]


def list_open_vacancies() -> list[dict]:
    result = (
        _client.table("vacancies")
        .select("*")
        .eq("status", "open")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


def get_vacancy(vacancy_id: str) -> dict | None:
    result = _client.table("vacancies").select("*").eq("id", vacancy_id).execute()
    return result.data[0] if result.data else None


def create_candidate(
    vacancy_id: str,
    file_name: str,
    resume_text: str,
    score: int,
    summary: str,
    strengths: str,
    gaps: str,
    recommendation: str,
    uploaded_by: int,
) -> dict:
    result = (
        _client.table("candidates")
        .insert(
            {
                "vacancy_id": vacancy_id,
                "file_name": file_name,
                "resume_text": resume_text,
                "score": score,
                "summary": summary,
                "strengths": strengths,
                "gaps": gaps,
                "recommendation": recommendation,
                "uploaded_by": uploaded_by,
            }
        )
        .execute()
    )
    return result.data[0]


def list_candidates(vacancy_id: str) -> list[dict]:
    result = (
        _client.table("candidates")
        .select("*")
        .eq("vacancy_id", vacancy_id)
        .order("score", desc=True)
        .execute()
    )
    return result.data


def get_candidate(candidate_id: str) -> dict | None:
    result = _client.table("candidates").select("*").eq("id", candidate_id).execute()
    return result.data[0] if result.data else None


def update_candidate_status(candidate_id: str, status: str) -> None:
    _client.table("candidates").update({"status": status}).eq("id", candidate_id).execute()


def search_vacancies(query: str) -> list[dict]:
    result = (
        _client.table("vacancies")
        .select("*")
        .eq("status", "open")
        .ilike("title", f"%{query}%")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


def search_candidates(query: str) -> list[dict]:
    result = (
        _client.table("candidates")
        .select("*, vacancies(title)")
        .ilike("file_name", f"%{query}%")
        .order("score", desc=True)
        .execute()
    )
    return result.data


def get_session(chat_id: int) -> dict:
    result = _client.table("chat_sessions").select("*").eq("chat_id", chat_id).execute()
    if not result.data:
        return {"history": [], "pending_upload": None}
    row = result.data[0]
    return {"history": row.get("history") or [], "pending_upload": row.get("pending_upload")}


def save_session(chat_id: int, history: list[dict], pending_upload: dict | None) -> None:
    _client.table("chat_sessions").upsert(
        {"chat_id": chat_id, "history": history, "pending_upload": pending_upload}
    ).execute()
