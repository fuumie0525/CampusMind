# CampusMind Frontend

CampusMind 校园多 Agent 咨询服务系统的 Vue 3 前端，连接 FastAPI 后端。

## 功能

- 校园咨询对话：校园政策、学生事务、校园网络、校园卡和宿舍后勤。
- 展示意图类别、Agent 类型、RAG 使用情况、工具调用和响应耗时。
- 健康检查、Monitor 状态查看和知识库片段统计。
- 校园知识库检索、文档导入和文件上传。
- 支持 Vite 开发代理以及 Docker + Nginx 部署。

## 默认地址

| 服务 | 地址 |
|---|---|
| CampusMind 后端 | `http://localhost:8000` |
| 前端开发地址 | `http://localhost:5173` |
| 前端 Docker 地址 | `http://localhost:5174` |

开发模式下，前端请求 `/api/campusmind`，Vite 会代理到 `http://localhost:8000`。

## 本地运行

先启动 CampusMind 后端，再执行：

```bash
npm install
npm run dev
```

访问：

```text
http://localhost:5173
```

后端地址不是默认值时：

```bash
VITE_CAMPUSMIND_API_URL=http://localhost:8000 npm run dev
```

## 构建检查

```bash
npm run build
```

## Docker 部署

```bash
npm run build
docker compose up -d --build
```

访问：

```text
http://localhost:5174
```

## 接口对应

前端使用以下 CampusMind 接口：

- `GET /health`
- `GET /monitor`
- `POST /chat`
- `POST /search`
- `GET /knowledge/stats`
- `POST /knowledge/add`
- `POST /knowledge/upload`
