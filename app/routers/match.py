import hashlib
import logging

from fastapi import APIRouter, HTTPException

from app.schemas.resume import MatchDetail, ResumeMatchRequest, ResumeMatchResponse
from app.services.cache import cache_service
from app.services.pdf_parser import deserialize_extracted
from app.services.qwen_client import match_resume

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/resume", tags=["resume"])

CACHE_PARSE_PREFIX = "resume:parse:"
CACHE_MATCH_PREFIX = "resume:match:"


@router.post("/match", response_model=ResumeMatchResponse)
async def match_job(request: ResumeMatchRequest) -> ResumeMatchResponse:
    logger.info(
        "match start resume_id=%s jd_len=%s",
        request.resume_id,
        len(request.job_description),
    )

    parse_key = f"{CACHE_PARSE_PREFIX}{request.resume_id}"
    parsed = cache_service.get(parse_key)
    if not parsed:
        logger.warning("match resume not found resume_id=%s", request.resume_id)
        raise HTTPException(
            status_code=404,
            detail="未找到该简历，请先调用 /api/resume/upload 上传",
        )

    job_hash = hashlib.sha256(request.job_description.encode()).hexdigest()[:16]
    match_cache_key = f"{CACHE_MATCH_PREFIX}{request.resume_id}:{job_hash}"
    cached_match = cache_service.get(match_cache_key)
    if cached_match:
        logger.info("match cache hit resume_id=%s", request.resume_id)
        return ResumeMatchResponse(
            resume_id=request.resume_id,
            cached=True,
            job_keywords=cached_match["job_keywords"],
            match=MatchDetail.model_validate(cached_match["match"]),
        )

    extracted = deserialize_extracted(parsed["extracted"])

    try:
        logger.info("qwen match start resume_id=%s", request.resume_id)
        job_keywords, match = match_resume(request.job_description, extracted)
        logger.info(
            "qwen match ok resume_id=%s ai_score=%s skill=%s",
            request.resume_id,
            match.ai_score,
            match.skill_match_rate,
        )
    except RuntimeError as exc:
        logger.error("qwen match config/api error resume_id=%s: %s", request.resume_id, exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("qwen match failed resume_id=%s", request.resume_id)
        raise HTTPException(status_code=502, detail=f"AI 匹配评分失败: {exc}") from exc

    cache_service.set(
        match_cache_key,
        {
            "job_keywords": job_keywords,
            "match": match.model_dump(),
        },
    )

    return ResumeMatchResponse(
        resume_id=request.resume_id,
        cached=False,
        job_keywords=job_keywords,
        match=match,
    )
