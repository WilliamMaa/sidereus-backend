# 前端对接文档

本文档供 **Next.js 前端仓库** 对接 `sidereus-backend` 使用。

## 1. 联调流程概览

```
用户上传 PDF
    ↓
POST /api/resume/upload  →  拿到 resume_id + 提取信息
    ↓
用户填写岗位 JD
    ↓
POST /api/resume/match   →  拿到匹配评分（需先有 resume_id）
```

**重要：** `/match` 依赖 `/upload` 的结果。前端需在 state 中保存 `resume_id`（上传响应里返回），匹配时一并提交。

---

## 2. 环境变量

前端项目（Vercel / 本地）需配置：

```env
# 后端 API 根地址，不要带末尾斜杠
NEXT_PUBLIC_API_URL=http://localhost:9000
```

部署后改为 FC 公网地址，例如：

```env
NEXT_PUBLIC_API_URL=https://xxx.cn-hangzhou.fc.aliyuncs.com
```

---

## 3. 本地启动后端（给前端联调用）

在后端仓库根目录：

```bash
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY

docker compose up --build
```

- API 地址：`http://localhost:9000`
- Swagger 文档：`http://localhost:9000/docs`
- 健康检查：`http://localhost:9000/health`

**现阶段可不配 Redis**：后端会自动降级为进程内内存缓存，本地单进程联调足够。

> FC 线上若无 Redis，内存缓存在不同实例间不共享；演示时建议 upload 后立刻 match，或接 Upstash。

---

## 4. CORS

后端通过 `CORS_ORIGINS` 控制跨域。本地开发可设为 `*`，部署时在 FC 环境变量里填前端域名：

```env
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

前端直接用 `fetch` 调后端即可，**不需要** Next.js API Route 做代理（除非你想规避 CORS）。

---

## 5. API 接口

### 5.1 健康检查

```
GET /health
```

**响应 200：**

```json
{
  "status": "ok",
  "redis": "ok"
}
```

`redis` 取值：

| 值 | 含义 |
|----|------|
| `ok` | Redis 正常 |
| `memory` | 无 Redis，使用内存缓存 |
| `unavailable` | Redis 配置了但连不上 |

可用于页面加载时检测后端是否在线。

---

### 5.2 上传并解析简历

```
POST /api/resume/upload
Content-Type: multipart/form-data
```

**请求：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | File | PDF 文件，字段名必须是 `file` |

**成功响应 200：**

```json
{
  "resume_id": "a1b2c3...（64 位 SHA256）",
  "cached": false,
  "page_count": 2,
  "cleaned_text_preview": "张三\n电话：138...",
  "extracted": {
    "basic": {
      "name": "张三",
      "phone": "13800138000",
      "email": "zhangsan@example.com",
      "address": "北京市朝阳区"
    },
    "job": {
      "job_intention": "Python 后端开发",
      "expected_salary": "20-25K"
    },
    "background": {
      "work_years": "3年",
      "education": "本科 · 计算机科学",
      "projects": ["电商后台系统", "简历分析平台"]
    }
  }
}
```

**字段说明：**

| 字段 | 说明 |
|------|------|
| `resume_id` | **必须保存**，后续 `/match` 要用 |
| `cached` | `true` 表示命中缓存，未重新调 AI |
| `page_count` | PDF 页数 |
| `cleaned_text_preview` | 清洗后文本预览（最多约 500 字） |
| `extracted.basic` | 基本信息（必选字段） |
| `extracted.job` | 求职信息（可能为 null） |
| `extracted.background` | 背景信息（可能为 null） |

**耗时：** 首次上传约 **5–15 秒**（PDF 解析 + Qwen 提取），前端请加 loading。

**错误响应：**

| 状态码 | detail 示例 | 原因 |
|--------|-------------|------|
| 400 | `仅支持 PDF 格式简历` | 非 PDF |
| 400 | `文件为空` | 空文件 |
| 422 | `PDF 解析失败: ...` | PDF 损坏或无法解析 |
| 422 | `未能从 PDF 中提取到文本` | 扫描件/图片 PDF |
| 502 | `AI 信息提取失败: ...` | Qwen 返回异常 |
| 503 | `DASHSCOPE_API_KEY 未配置` | 后端未配 API Key |

---

### 5.3 岗位匹配评分

```
POST /api/resume/match
Content-Type: application/json
```

**请求体：**

```json
{
  "resume_id": "a1b2c3...",
  "job_description": "招聘 Python 后端工程师，要求熟悉 FastAPI、Redis，3年以上经验..."
}
```

| 字段 | 类型 | 约束 |
|------|------|------|
| `resume_id` | string | 必填，来自 upload 响应 |
| `job_description` | string | 必填，至少 10 个字符 |

**成功响应 200：**

```json
{
  "resume_id": "a1b2c3...",
  "cached": false,
  "job_keywords": ["Python", "FastAPI", "Redis", "后端"],
  "match": {
    "skill_match_rate": 85.0,
    "experience_relevance": 78.0,
    "matched_keywords": ["Python", "FastAPI"],
    "missing_keywords": ["Kubernetes"],
    "ai_score": 82.0,
    "ai_summary": "候选人 Python 和后端经验与岗位高度匹配，缺少 K8s 相关经验..."
  }
}
```

**字段说明：**

| 字段 | 说明 |
|------|------|
| `job_keywords` | 从 JD 提取的关键词 |
| `match.skill_match_rate` | 技能匹配率 0–100 |
| `match.experience_relevance` | 经验相关性 0–100 |
| `match.matched_keywords` | 已匹配关键词 |
| `match.missing_keywords` | 缺失关键词 |
| `match.ai_score` | AI 综合评分 0–100 |
| `match.ai_summary` | AI 分析摘要（展示用） |

**耗时：** 约 **5–10 秒**，前端请加 loading。

**错误响应：**

| 状态码 | detail 示例 | 原因 |
|--------|-------------|------|
| 404 | `未找到该简历，请先调用 /api/resume/upload 上传` | resume_id 无效或缓存已失效 |
| 422 | 校验错误 | job_description 太短 |
| 502/503 | AI 相关错误 | 同 upload |

---

## 6. TypeScript 类型（可直接复制到前端）

```typescript
// lib/types.ts

export interface BasicInfo {
  name: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
}

export interface JobInfo {
  job_intention: string | null;
  expected_salary: string | null;
}

export interface BackgroundInfo {
  work_years: string | null;
  education: string | null;
  projects: string[];
}

export interface ExtractedInfo {
  basic: BasicInfo;
  job: JobInfo;
  background: BackgroundInfo;
}

export interface ResumeUploadResponse {
  resume_id: string;
  cached: boolean;
  page_count: number;
  cleaned_text_preview: string;
  extracted: ExtractedInfo;
}

export interface MatchDetail {
  skill_match_rate: number;
  experience_relevance: number;
  matched_keywords: string[];
  missing_keywords: string[];
  ai_score: number;
  ai_summary: string;
}

export interface ResumeMatchResponse {
  resume_id: string;
  cached: boolean;
  job_keywords: string[];
  match: MatchDetail;
}

export interface ApiError {
  detail: string;
}
```

---

## 7. API 封装示例

```typescript
// lib/api.ts

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:9000";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "请求失败");
  }
  return res.json();
}

export async function checkHealth() {
  const res = await fetch(`${API_URL}/health`);
  return handleResponse<{ status: string; redis: string }>(res);
}

export async function uploadResume(file: File) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_URL}/api/resume/upload`, {
    method: "POST",
    body: form,
  });
  return handleResponse<import("./types").ResumeUploadResponse>(res);
}

export async function matchResume(resumeId: string, jobDescription: string) {
  const res = await fetch(`${API_URL}/api/resume/match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      resume_id: resumeId,
      job_description: jobDescription,
    }),
  });
  return handleResponse<import("./types").ResumeMatchResponse>(res);
}
```

---

## 8. 建议的页面结构

单页即可，分三个区域：

### Step 1 — 上传简历
- 文件选择器，**仅接受 `.pdf`**
- 上传按钮 + 进度/loading（预计 5–15s）
- 成功后展示：
  - 基本信息卡片（姓名、电话、邮箱、地址）
  - 求职信息（有则展示）
  - 背景信息（学历、年限、项目列表）
  - 文本预览（`cleaned_text_preview`）
  - 若 `cached === true` 可显示「来自缓存」标签

### Step 2 — 岗位匹配
- 多行文本框输入 JD（≥ 10 字）
- 「开始匹配」按钮 + loading（预计 5–10s）
- **禁用条件：** 没有 `resume_id` 时不可点

### Step 3 — 匹配结果
- 综合评分：`match.ai_score`（大号数字 / 进度环）
- 技能匹配率、经验相关性（两个子指标）
- 关键词：绿色 tag = `matched_keywords`，红色 tag = `missing_keywords`
- AI 摘要：`match.ai_summary`

---

## 9. 前端状态管理建议

```typescript
// 最小 state
const [resumeId, setResumeId] = useState<string | null>(null);
const [uploadResult, setUploadResult] = useState<ResumeUploadResponse | null>(null);
const [matchResult, setMatchResult] = useState<ResumeMatchResponse | null>(null);
const [loading, setLoading] = useState<"upload" | "match" | null>(null);
const [error, setError] = useState<string | null>(null);
```

流程：

1. 上传成功 → `setResumeId(data.resume_id)` + `setUploadResult(data)`
2. 点击匹配 → 用 `resumeId` 调 `matchResume`
3. 用户重新上传 → 清空 match 结果，更新 resumeId

---

## 10. 联调 Checklist

- [ ] 后端 `docker compose up` 跑起来
- [ ] 浏览器访问 `http://localhost:9000/health` 返回 `{"status":"ok"}`
- [ ] 前端 `.env.local` 设 `NEXT_PUBLIC_API_URL=http://localhost:9000`
- [ ] 上传一份 PDF，确认返回 `resume_id` 和 `extracted`
- [ ] 填入 JD，确认返回 `match.ai_score`
- [ ] 部署前端后，后端 `CORS_ORIGINS` 加上 Vercel 域名

---

## 11. curl 快速测试（不依赖前端）

```bash
# 健康检查
curl http://localhost:9000/health

# 上传
curl -X POST http://localhost:9000/api/resume/upload \
  -F "file=@/path/to/resume.pdf"

# 匹配（替换 resume_id）
curl -X POST http://localhost:9000/api/resume/match \
  -H "Content-Type: application/json" \
  -d '{"resume_id":"<resume_id>","job_description":"招聘 Python 后端，熟悉 FastAPI，3年经验"}'
```

---

## 12. 常见问题

**Q: 上传成功但 match 返回 404？**  
A: `resume_id` 错误或后端重启导致内存缓存丢失。重新 upload 后再 match。

**Q: 跨域报错？**  
A: 检查后端 `CORS_ORIGINS` 是否包含前端 origin。

**Q: 上传很慢？**  
A: 正常，Qwen API 调用需要时间。不要设太短的 fetch timeout。

**Q: 扫描版 PDF 解析失败？**  
A: 当前只支持文本型 PDF，不支持 OCR。换一份可选中文字的 PDF 测试。

---

## 13. 后端仓库信息

- 仓库：`sidereus-backend`
- 交互式文档：`<API_URL>/docs`（Swagger UI，可直接试接口）
- OpenAPI JSON：`<API_URL>/openapi.json`（可用 openapi-typescript 自动生成类型）
