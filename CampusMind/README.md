# CampusMind 校园多 Agent 咨询服务系统

CampusMind 是一个基于 FastAPI 的校园多 Agent 智能咨询项目，面向校园政策问答、学生事务办理、校园网络排障、校园卡缴费咨询和宿舍后勤服务。

项目重点展示以下工程链路：

- 三路融合意图识别：LLM Few-shot、轻量 Embedding 相似度和关键词规则加权投票，低置信度降级为 `other`。
- 多 Agent 编排：按意图路由到 `affairs`、`network`、`campus_card` 或 `general`，复合问题支持并行处理与结果聚合。
- RAG 知识库：ChromaDB 文档切片、查询改写、多路并行召回、去重和 LLM 重排。
- 校园工具调用：学生事务流程、校园网自查、校园卡指引和宿舍报修指引接入 `/chat` 主链路。
- 分层会话记忆：Redis 保存短期工作记忆，ChromaDB 保存历史摘要和用户画像。
- 在线监控闭环：采集 Agent/工具成功率和延迟，Monitor 将惩罚项写回动态路由评分。
- 自动评测：意图 Accuracy/Macro-F1，以及 LLM-as-Judge 的相关性、准确性、完整性和有用性评分。

> 仓库内校园政策和工具数据均为演示内容，不代表任何具体学校的正式规定，也不会执行真实审批、充值、挂失、缴费或报修操作。

## 目录结构

```text
CampusMind/
├─ api/main.py                    # FastAPI 入口与 /chat 主链路
├─ core/
│  ├─ intent_recognizer.py        # 三路融合意图识别
│  └─ skill_loader.py             # 动态 Skills 加载与热更新
├─ agents/agent_orchestrator.py   # 多 Agent 路由、并行协作和降级
├─ mcp/
│  ├─ tool_manager.py             # 参数校验、TTL、超时、熔断、fallback、重排
│  ├─ knowledge_base.py           # ChromaDB RAG 知识库
│  └─ campus_tools.py             # 校园事务、网络、校园卡、宿舍工具
├─ memory/conversation_memory.py  # Redis + ChromaDB 分层记忆
├─ monitor/performance_monitor.py # 在线指标、异常检测和路由惩罚
├─ evaluation/evaluator.py        # LLM-as-Judge 与回归检测
├─ skills/                        # 可热加载校园业务规则
├─ data/demo_docs/                # 演示知识库文档
├─ docker-compose.yml             # API、Redis、ChromaDB、Prometheus、Nginx
└─ .env.example                   # 安全配置模板
```

## Agent 与意图

| Agent | 主要意图 | 典型问题 |
|---|---|---|
| `general` | 问候、投诉、反馈、低置信度问题 | “这个事情应该找哪个部门？” |
| `affairs` | `campus_policy`、`student_affairs`、`dorm_service` | 奖助学金、在读证明、学生证、宿舍报修 |
| `network` | `network_support` | 校园网认证、WiFi、VPN、断网 |
| `campus_card` | `campus_card` | 充值、挂失、补卡、异常扣费、缴费 |

路由评分为：

```text
routing_score = (success_rate × 0.7 + latency_score × 0.3) × (1 - monitor_penalty)
```

## 本地运行

### 1. 创建配置

```bash
cp .env.example .env
```

编辑 `.env`，至少填写：

```env
DEEPSEEK_API_KEY=你的密钥
LLM_MODEL=deepseek-v4-flash
LLM_BASE_URL=https://api.deepseek.com/anthropic
```

当前代码使用 Anthropic SDK 消息接口，因此 `LLM_BASE_URL` 需要是 Anthropic-compatible 端点。也可以继续使用 `ANTHROPIC_API_KEY`、`ANTHROPIC_MODEL` 和 `ANTHROPIC_BASE_URL`。

### 2. Docker Compose 启动

```bash
docker compose up -d --build
```

启动后：

- Swagger：`http://localhost/docs`
- 健康检查：`http://localhost/health`
- Prometheus：`http://localhost:9090`
- ChromaDB：`http://localhost:8001`

### 3. 导入演示知识

```bash
curl -X POST "http://localhost/knowledge/upload" \
  -F "file=@data/demo_docs/troubleshooting.md"
```

## 主要接口

### 对话

```http
POST /chat
Content-Type: application/json

{
  "message": "校园网认证失败，而且校园卡也充值不了",
  "user_id": "demo_student",
  "conv_id": "demo_conv"
}
```

响应会返回意图、Agent、是否使用知识库以及实际调用的校园工具：

```json
{
  "conv_id": "demo_conv",
  "response": "...",
  "intent": "network_support",
  "agent_type": "network",
  "escalated": false,
  "latency_ms": 1200.0,
  "knowledge_used": true,
  "tools_used": ["network_self_check", "campus_card_guide"]
}
```

其他接口：

- `POST /search`：查询改写、多路召回和 LLM 重排。
- `POST /knowledge/add`：批量导入知识文档。
- `POST /knowledge/upload`：上传 Markdown、TXT 或 JSON。
- `GET /skills`、`POST /skills/reload`：查看和热加载 Skills。
- `GET /monitor`、`GET /metrics`：监控摘要与 Prometheus 指标。
- `POST /eval/run`：运行校园意图和对话质量评测。

## 安全说明

- `.env`、本地 Chroma 数据、日志和评测基线已加入 `.gitignore`。
- 不要上传真实学生对话、学号、联系方式、支付记录或学校内部文件。
- 业务工具当前只返回流程指引。接入真实教务、一卡通或后勤系统时，应增加鉴权、权限控制、审计日志、数据脱敏和幂等处理。
- 示例知识需要替换为学校权威材料，并记录来源、发布日期、适用范围和失效时间。

## 简历表述边界

代码能够支撑“三路意图识别、RAG、多 Agent 路由、分层记忆、Monitor、LLM-as-Judge、Docker Compose、Prometheus 和 Nginx”等描述。

当前校园业务工具是可运行的演示实现，并未接入学校真实系统，因此简历中适合写“校园卡缴费咨询、流程指引、工具调用框架”，不应写“完成真实缴费、查询真实余额、实际挂失或创建真实报修工单”。
