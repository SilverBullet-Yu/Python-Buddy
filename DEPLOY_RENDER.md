# Render 快速部署说明

## 部署目标

本方案把 FastAPI 后端、静态前端和网页 agent 放在同一个 Render Web Service 中运行。部署后，公网用户直接访问 Render 提供的 HTTPS 地址，不再依赖本机 FastAPI、Cloudflare Tunnel 或电脑开机状态。

## 部署步骤

1. 将当前项目推送到 GitHub 仓库。
2. 打开 Render，创建新的 Web Service。
3. 连接该 GitHub 仓库。
4. Render 会读取 `render.yaml`，使用以下命令部署：
   - 构建命令：`pip install -r requirements-render.txt`
   - 启动命令：`python src/main.py -m http`
5. 在 Render 的环境变量页面填写：
   - `OPENAI_API_KEY`：模型 API Key。
   - `OPENAI_BASE_URL`：OpenAI 兼容模型网关地址。如果使用官方 OpenAI，可以留空。
6. 部署完成后访问 Render 分配的公网地址。

## 可选环境变量

如果需要持久化对话、学习进度和错题记录，需要配置 Supabase：

- `COZE_SUPABASE_URL`
- `COZE_SUPABASE_ANON_KEY`
- `COZE_SUPABASE_SERVICE_ROLE_KEY`

如果不配置 Supabase，基础网页和 agent 对话仍可运行，但保存历史、进度、错题等依赖数据库的功能会不可用或降级。

如果需要 `/refresh-frontend` 上传前端到对象存储，需要额外配置：

- `COZE_BUCKET_ENDPOINT_URL`
- `COZE_BUCKET_NAME`
- `COZE_WORKLOAD_IDENTITY_CLIENT_ID`
- `COZE_WORKLOAD_IDENTITY_CLIENT_SECRET`
- `COZE_WORKLOAD_IDENTITY_TOKEN_ENDPOINT`
- `COZE_WORKLOAD_ACCESS_TOKEN_ENDPOINT`

快速公网部署不依赖 `/refresh-frontend`，因为前端已由 FastAPI 直接提供。

## 验证

部署完成后访问：

- `/health`：应返回服务运行状态。
- `/`：应打开网页。
- 网页中发送一条消息：应能通过 `/stream_run` 与 agent 交互。