import json
import logging
import re
from typing import Any

import dashscope
from dashscope import Generation

from app.config import settings
from app.schemas.resume import BackgroundInfo, BasicInfo, ExtractedInfo, JobInfo, MatchDetail

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """你是专业的 HR 简历解析助手。请从以下简历文本中提取结构化信息，严格以 JSON 格式返回，不要包含任何其他文字。

JSON 结构：
{
  "basic": {"name": "姓名或null", "phone": "电话或null", "email": "邮箱或null", "address": "地址或null"},
  "job": {"job_intention": "求职意向或null", "expected_salary": "期望薪资或null"},
  "background": {"work_years": "工作年限或null", "education": "学历背景或null", "projects": ["项目1", "项目2"]}
}

简历文本：
{resume_text}
"""

MATCH_PROMPT = """你是专业的招聘顾问。请根据岗位需求和候选人简历信息，进行匹配分析。

岗位需求：
{job_description}

候选人信息（JSON）：
{resume_json}

请严格以 JSON 格式返回，不要包含任何其他文字：
{
  "skill_match_rate": 0-100的数字,
  "experience_relevance": 0-100的数字,
  "matched_keywords": ["匹配到的关键词"],
  "missing_keywords": ["缺失的关键词"],
  "ai_score": 0-100的综合评分,
  "ai_summary": "100字以内的匹配分析摘要"
}
"""


def _ensure_api_key() -> None:
    if not settings.dashscope_api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置")
    dashscope.api_key = settings.dashscope_api_key


def _call_qwen(prompt: str) -> str:
    _ensure_api_key()
    response = Generation.call(
        model=settings.qwen_model,
        messages=[{"role": "user", "content": prompt}],
        result_format="message",
    )
    if response.status_code != 200:
        raise RuntimeError(f"DashScope API 错误: {response.code} - {response.message}")

    content = response.output.choices[0].message.content
    return content.strip()


def _parse_json_from_response(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def extract_resume_info(resume_text: str) -> ExtractedInfo:
    truncated = resume_text[:12000]
    prompt = EXTRACT_PROMPT.format(resume_text=truncated)
    raw = _call_qwen(prompt)
    data = _parse_json_from_response(raw)

    return ExtractedInfo(
        basic=BasicInfo.model_validate(data.get("basic", {})),
        job=JobInfo.model_validate(data.get("job", {})),
        background=BackgroundInfo.model_validate(data.get("background", {})),
    )


def extract_job_keywords(job_description: str) -> list[str]:
    prompt = f"""从以下岗位需求中提取 5-15 个关键技能/要求关键词，以 JSON 数组返回，不要其他文字。

岗位需求：
{job_description[:4000]}
"""
    raw = _call_qwen(prompt)
    try:
        keywords = _parse_json_from_response(raw) if raw.startswith("{") else json.loads(raw)
        if isinstance(keywords, dict) and "keywords" in keywords:
            keywords = keywords["keywords"]
        if isinstance(keywords, list):
            return [str(k) for k in keywords[:15]]
    except json.JSONDecodeError:
        pass
    return re.findall(r"[\u4e00-\u9fffA-Za-z0-9+#.]{2,}", job_description)[:10]


def match_resume(job_description: str, extracted: ExtractedInfo) -> tuple[list[str], MatchDetail]:
    resume_json = json.dumps(extracted.model_dump(), ensure_ascii=False)
    prompt = MATCH_PROMPT.format(job_description=job_description[:4000], resume_json=resume_json)
    raw = _call_qwen(prompt)
    data = _parse_json_from_response(raw)

    keywords = data.get("matched_keywords", []) + data.get("missing_keywords", [])
    job_keywords = list(dict.fromkeys(str(k) for k in keywords))[:15]
    if not job_keywords:
        job_keywords = extract_job_keywords(job_description)

    match = MatchDetail(
        skill_match_rate=float(data.get("skill_match_rate", 0)),
        experience_relevance=float(data.get("experience_relevance", 0)),
        matched_keywords=[str(k) for k in data.get("matched_keywords", [])],
        missing_keywords=[str(k) for k in data.get("missing_keywords", [])],
        ai_score=float(data.get("ai_score", 0)),
        ai_summary=str(data.get("ai_summary", "")),
    )
    return job_keywords, match
