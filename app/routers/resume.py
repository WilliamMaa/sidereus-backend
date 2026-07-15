import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.resume import ResumeUploadResponse
from app.services.cache import cache_service
from app.services.pdf_parser import (
    compute_file_hash,
    deserialize_extracted,
    parse_pdf,
    serialize_extracted,
    text_preview,
)
from app.services.qwen_client import extract_resume_info

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/resume", tags=["resume"])

CACHE_PARSE_PREFIX = "resume:parse:"


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)) -> ResumeUploadResponse:
    filename = file.filename or ""
    logger.info("upload start filename=%s content_type=%s", filename, file.content_type)

    if not filename.lower().endswith(".pdf"):
        logger.warning("upload reject: not pdf filename=%s", filename)
        raise HTTPException(status_code=400, detail="仅支持 PDF 格式简历")

    content = await file.read()
    size = len(content)
    logger.info("upload read bytes=%s", size)
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    resume_id = compute_file_hash(content)
    cache_key = f"{CACHE_PARSE_PREFIX}{resume_id}"
    logger.info("upload resume_id=%s", resume_id)

    cached = cache_service.get(cache_key)
    if cached:
        logger.info("upload cache hit resume_id=%s", resume_id)
        extracted = deserialize_extracted(cached["extracted"])
        return ResumeUploadResponse(
            resume_id=resume_id,
            cached=True,
            page_count=cached["page_count"],
            cleaned_text_preview=cached["cleaned_text_preview"],
            extracted=extracted,
        )

    try:
        cleaned_text, page_count = parse_pdf(content)
        logger.info(
            "pdf parsed pages=%s text_len=%s preview=%s",
            page_count,
            len(cleaned_text),
            cleaned_text[:120].replace("\n", " "),
        )
    except Exception as exc:
        logger.exception("PDF 解析失败 resume_id=%s", resume_id)
        raise HTTPException(status_code=422, detail=f"PDF 解析失败: {exc}") from exc

    if not cleaned_text:
        logger.warning("PDF 无文本 resume_id=%s", resume_id)
        raise HTTPException(status_code=422, detail="未能从 PDF 中提取到文本")

    try:
        logger.info("qwen extract start resume_id=%s", resume_id)
        extracted = extract_resume_info(cleaned_text)
        logger.info(
            "qwen extract ok resume_id=%s name=%s email=%s",
            resume_id,
            extracted.basic.name,
            extracted.basic.email,
        )
    except RuntimeError as exc:
        logger.error("qwen extract config/api error resume_id=%s: %s", resume_id, exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("qwen extract failed resume_id=%s", resume_id)
        raise HTTPException(status_code=502, detail=f"AI 信息提取失败: {exc}") from exc

    preview = text_preview(cleaned_text)
    cache_service.set(
        cache_key,
        {
            "page_count": page_count,
            "cleaned_text": cleaned_text,
            "cleaned_text_preview": preview,
            "extracted": serialize_extracted(extracted),
        },
    )
    logger.info("upload done resume_id=%s cached=false", resume_id)

    return ResumeUploadResponse(
        resume_id=resume_id,
        cached=False,
        page_count=page_count,
        cleaned_text_preview=preview,
        extracted=extracted,
    )
