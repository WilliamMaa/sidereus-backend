# Sidereus — AI 智能简历分析后端

基于 FastAPI + 通义千问（DashScope）+ Redis，适配阿里云函数计算 FC 3.0 部署。

## 功能

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/resume/upload` | POST | 上传 PDF 简历，解析文本并 AI 提取关键信息 |
| `/api/resume/match` | POST | 输入岗位 JD，计算匹配度评分 |
| `/health` | GET | 健康检查 |
| `/docs` | GET | Swagger 文档 |

## 本地开发

```bash
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY

docker compose up --build
```

访问 http://localhost:9000/docs

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `DASHSCOPE_API_KEY` | ✅ | 阿里云 DashScope API Key |
| `REDIS_URL` | ⭐ | Redis 连接地址，不填则缓存降级为无 |
| `QWEN_MODEL` | | 默认 `qwen-plus` |
| `CORS_ORIGINS` | | 前端域名，如 `https://xxx.vercel.app` |

## 部署到阿里云 FC

**地域：华北2（北京）`cn-beijing`**

推荐 **自定义容器**，详细步骤见：[docs/DEPLOY.md](docs/DEPLOY.md)

简要流程：

1. 开通 FC + ACR（北京）
2. `docker build` → 推送到 `registry.cn-beijing.aliyuncs.com/...`
3. FC 创建「容器镜像」函数，端口 **9000**，超时 **120s**
4. 环境变量至少配：
   - `DASHSCOPE_API_KEY`（必填）
   - `CACHE_ENABLED=false`（无 Redis 时可直接这样）
   - `CORS_ORIGINS`（前端域名）
5. HTTP 触发器开启 **Basic Auth**（用户名/密码在 FC 控制台配置）
6. 公网地址：`https://sidereu-backend-sqtlfffqho.cn-beijing.fcapp.run`
7. 前端用服务端环境变量 `FC_BASE_URL` + `FC_BASIC_AUTH_USER` / `FC_BASIC_AUTH_PASSWORD` 调用（见 `docs/FRONTEND.md`）

## 架构说明

- **无状态**：不在本地持久化业务数据，适合 Serverless
- **Redis 外置**：解析结果与匹配评分按 `resume_id` + JD hash 缓存
- **resume_id**：上传文件的 SHA256，相同文件命中缓存

## API 示例

### 上传简历

```bash
curl -X POST http://localhost:9000/api/resume/upload \
  -F "file=@resume.pdf"
```

### 岗位匹配

```bash
curl -X POST http://localhost:9000/api/resume/match \
  -H "Content-Type: application/json" \
  -d '{"resume_id": "<返回的 resume_id>", "job_description": "招聘 Python 后端，熟悉 FastAPI..."}'
```
