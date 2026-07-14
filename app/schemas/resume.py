from typing import Optional

from pydantic import BaseModel, Field


class BasicInfo(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class JobInfo(BaseModel):
    job_intention: Optional[str] = Field(None, description="求职意向")
    expected_salary: Optional[str] = Field(None, description="期望薪资")


class BackgroundInfo(BaseModel):
    work_years: Optional[str] = Field(None, description="工作年限")
    education: Optional[str] = Field(None, description="学历背景")
    projects: Optional[list[str]] = Field(default_factory=list, description="项目经历")


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
