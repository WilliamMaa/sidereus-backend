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

### 方式一：Custom Runtime（代码包）

1. 安装 [Serverless Devs](https://docs.serverless-devs.com/)
2. 配置阿里云账号：`s config add`
3. 设置环境变量后部署：

```bash
export DASHSCOPE_API_KEY=sk-xxx
export REDIS_URL=redis://your-redis:6379/0
export CORS_ORIGINS=https://your-frontend.vercel.app

s deploy
```

FC 会执行 `bootstrap` 启动 uvicorn，监听 **9000** 端口。

### 方式二：自定义容器

```bash
docker build -t sidereus-backend .
# 推送至阿里云 ACR，在 FC 控制台创建容器函数，端口 9000
```

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
