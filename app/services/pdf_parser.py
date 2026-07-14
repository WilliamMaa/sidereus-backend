import hashlib
import json
import re

import fitz

from app.schemas.resume import ExtractedInfo


def compute_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parse_pdf(content: bytes) -> tuple[str, int]:
    """Extract and clean text from a multi-page PDF."""
    doc = fitz.open(stream=content, filetype="pdf")
    try:
        pages: list[str] = []
        for page in doc:
            text = page.get_text("text")
            if text.strip():
                pages.append(text)
        page_count = len(doc)
    finally:
        doc.close()

    raw = "\n\n".join(pages)
    cleaned = clean_text(raw)
    return cleaned, page_count


def clean_text(text: str) -> str:
    """Remove redundant characters and normalize paragraph breaks."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)
    return text.strip()


def text_preview(text: str, max_len: int = 500) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def serialize_extracted(info: ExtractedInfo) -> dict:
    return info.model_dump()


def deserialize_extracted(data: dict) -> ExtractedInfo:
    return ExtractedInfo.model_validate(data)
