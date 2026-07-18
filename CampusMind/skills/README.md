# CampusMind Skills

Skills 是可热加载的校园业务规则，会按 Agent 类型和关键词动态注入 system prompt。

```text
skills/general_campus_service/SKILL.md  # 综合接待与分流
skills/campus_affairs/SKILL.md          # 校园政策、学生事务、宿舍后勤
skills/campus_network/SKILL.md          # 校园网、WiFi、VPN 排查
skills/campus_card/SKILL.md             # 校园卡和缴费咨询
```

每个 `SKILL.md` 顶部使用简化 front matter：

```yaml
---
name: 校园网络故障排查规范
description: 业务说明
keywords: 校园网,WiFi,VPN
agents: network
enabled: true
---
```

可通过 `POST /skills/reload` 热加载，无需重启服务。支持的 Agent 值为 `general`、`affairs`、`network`、`campus_card`。
