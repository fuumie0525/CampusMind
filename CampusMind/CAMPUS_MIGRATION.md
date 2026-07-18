# EchoMind → CampusMind 改造说明

## 已完成的业务改造

| 原客服域 | CampusMind 校园域 |
|---|---|
| Query / Account | 校园政策、学生事务 |
| TechnicalAgent | NetworkAgent：校园网、WiFi、VPN、认证故障 |
| BillingAgent | CampusCardAgent：充值、挂失、补卡、异常扣费与缴费咨询 |
| 通用售后 Skill | 校园综合咨询与分流 Skill |
| 退款/订单知识库 | 在读证明、奖助学金、校园网、校园卡、宿舍报修知识库 |
| 电商评测用例 | 校园政策、网络、校园卡、宿舍和多轮学生事务用例 |

## 新增代码

- `mcp/campus_tools.py`
  - `affairs_process_guide`
  - `network_self_check`
  - `campus_card_guide`
  - `dorm_service_guide`
- `/chat` 会并行执行 RAG 和校园业务工具，并在响应中返回 `tools_used`。
- 新增 4 份校园 Skills 和 6 项核心逻辑测试。

## 仓库清理

最终版本已经删除：

- 真实 `.env` 和非空 API Key
- `.venv`
- `.git`
- `.idea`
- `__MACOSX`、`.DS_Store`
- 本地 ChromaDB 数据和旧电商评测基线

## 简历描述边界

可以写：校园政策问答、办事流程指导、校园网自助排查、校园卡缴费咨询、RAG、工具调用、多 Agent 路由、分层记忆、Monitor、LLM-as-Judge。

不能写：已经接入学校真实教务系统、查询真实校园卡余额、完成真实充值/挂失/缴费、创建真实报修工单。当前工具是可运行的流程演示和后续系统接入骨架。
