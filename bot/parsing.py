import io

import pdfplumber
from docx import Document

MAX_RESUME_CHARS = 20_000


class UnsupportedFileError(Exception):
    pass


def extract_text(file_bytes: bytes, filename: str) -> str:
    lower = filename.lower()

    if lower.endswith(".pdf"):
        text = _extract_pdf(file_bytes)
    elif lower.endswith(".docx"):
        text = _extract_docx(file_bytes)
    elif lower.endswith(".txt"):
        text = file_bytes.decode("utf-8", errors="ignore")
    else:
        raise UnsupportedFileError(
            "Поддерживаются только файлы .pdf, .docx или .txt."
        )

    text = text.strip()
    if not text:
        raise UnsupportedFileError("Не удалось извлечь текст из файла.")
    return text[:MAX_RESUME_CHARS]


def _extract_pdf(file_bytes: bytes) -> str:
    pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _extract_docx(file_bytes: bytes) -> str:
    document = Document(io.BytesIO(file_bytes))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)
