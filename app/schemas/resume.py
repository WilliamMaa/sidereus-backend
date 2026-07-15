from typing import Annotated, Any, Optional

from pydantic import BaseModel, BeforeValidator, Field


def _as_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        # 5 -> "5", 5.0 -> "5"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
    return str(value)


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            text = _as_optional_str(item)
            if text:
                result.append(text)
        return result
    text = _as_optional_str(value)
    return [text] if text else []


OptionalStr = Annotated[Optional[str], BeforeValidator(_as_optional_str)]
StrList = Annotated[list[str], BeforeValidator(_as_str_list)]


class BasicInfo(BaseModel):
    name: OptionalStr = None
    phone: OptionalStr = None
    email: OptionalStr = None
    address: OptionalStr = None


class JobInfo(BaseModel):
    job_intention: OptionalStr = Field(None, description="求职意向")
    expected_salary: OptionalStr = Field(None, description="期望薪资")


class BackgroundInfo(BaseModel):
    work_years: OptionalStr = Field(None, description="工作年限")
    education: OptionalStr = Field(None, description="学历背景")
    projects: StrList = Field(default_factory=list, description="项目经历")


class ExtractedInfo(BaseModel):
    basic: BasicInfo = Field(default_factory=BasicInfo)
    job: JobInfo = Field(default_factory=JobInfo)
    background: BackgroundInfo = Field(default_factory=BackgroundInfo)


class MatchDetail(BaseModel):
    skill_match_rate: float = Field(..., ge=0, le=100, description="技能匹配率 0-100")
    experience_relevance: float = Field(..., ge=0, le=100, description="工作经验相关性 0-100")
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    ai_score: float = Field(..., ge=0, le=100, description="AI 综合评分 0-100")
    ai_summary: str = Field("", description="AI 匹配分析摘要")


class ResumeUploadResponse(BaseModel):
    resume_id: str
    cached: bool
    page_count: int
    cleaned_text_preview: str
    extracted: ExtractedInfo


class ResumeMatchRequest(BaseModel):
    resume_id: str
    job_description: str = Field(..., min_length=10, description="招聘岗位需求描述")


class ResumeMatchResponse(BaseModel):
    resume_id: str
    cached: bool
    job_keywords: list[str]
    match: MatchDetail


class HealthResponse(BaseModel):
    status: str
    redis: str  # "ok" | "memory" | "unavailable"
