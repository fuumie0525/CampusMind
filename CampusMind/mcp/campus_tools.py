"""CampusMind 校园业务工具。

这些工具用于演示 MCPToolManager 的参数校验、TTL 缓存、超时、熔断和 fallback。
当前实现提供流程指引与自助排查，不连接学校真实教务、网管或一卡通系统。
接入真实系统时，只需要替换各 handler 的数据访问部分。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from mcp.tool_manager import MCPToolManager, Tool, ToolResult


_AFFAIRS_GUIDES: Dict[str, Dict[str, Any]] = {
    "在读证明": {
        "steps": ["登录学校办事大厅", "搜索“在读证明”服务", "核对个人信息并提交", "下载电子证明或按通知领取纸质件"],
        "materials": ["统一身份认证账号", "必要时填写证明用途"],
    },
    "学生证补办": {
        "steps": ["先挂失原学生证", "在办事大厅提交补办申请", "按要求上传照片或缴纳工本费", "等待学院或学生工作部门审核后领取"],
        "materials": ["本人身份信息", "近期证件照", "遗失情况说明（如学校要求）"],
    },
    "请假": {
        "steps": ["确认请假类型与天数", "在教务或学生工作系统发起申请", "上传必要证明", "等待辅导员、导师或学院审批"],
        "materials": ["请假起止时间", "请假原因", "相关证明材料（如适用）"],
    },
    "缓考": {
        "steps": ["查看本学期缓考申请通知", "在截止时间前提交申请", "上传医院证明或其他佐证", "等待学院和教务部门审核"],
        "materials": ["课程与考试信息", "缓考原因", "符合要求的证明材料"],
    },
    "奖助学金": {
        "steps": ["查看当年度评定通知", "确认申报条件", "按学院要求提交申请与证明", "关注公示和复核安排"],
        "materials": ["成绩或科研证明", "综合测评材料", "家庭经济情况材料（助学金适用）"],
    },
}


async def affairs_process_handler(params: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    service = str(params.get("service", "")).strip()
    matched = next((name for name in _AFFAIRS_GUIDES if name in service or service in name), None)
    if matched is None:
        return {
            "service": service,
            "matched": False,
            "guidance": "暂未匹配到固定流程，请通过学校办事大厅搜索事项名称，或联系学院辅导员/教务老师确认。",
            "official_notice_required": True,
        }
    guide = _AFFAIRS_GUIDES[matched]
    return {
        "service": matched,
        "matched": True,
        "steps": guide["steps"],
        "materials": guide["materials"],
        "official_notice_required": True,
        "notice": "各学校、学院和学期要求可能不同，请以当前官方通知为准。",
    }


async def network_diagnosis_handler(params: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    symptom = str(params.get("symptom", "")).strip()
    network_type = str(params.get("network_type", "校园网")).strip() or "校园网"
    steps: List[str] = [
        "确认同一地点的其他设备是否也无法联网，以区分个人设备与区域故障",
        "关闭并重新开启网络连接，重新选择校园网络",
        "打开认证页面，确认账号未欠费、未被锁定且登录状态未过期",
        "暂时关闭代理、VPN 或自定义 DNS 后重试",
        "记录发生时间、楼栋/区域、设备系统和错误提示，便于网络中心定位",
    ]
    if "vpn" in symptom.lower() or "vpn" in network_type.lower():
        steps = [
            "确认 VPN 客户端和配置文件为学校当前版本",
            "确认校园统一身份认证账号可正常登录",
            "检查系统时间是否准确，并暂时关闭冲突的代理软件",
            "切换网络后重试并记录错误码",
            "仍失败时将错误码、客户端版本和发生时间提交给网络中心",
        ]
    elif any(k in symptom for k in ["认证", "登录", "账号"]):
        steps.insert(2, "清除旧认证会话或忘记该网络后重新连接，再打开认证门户")

    return {
        "network_type": network_type,
        "symptom": symptom,
        "diagnosis_steps": steps,
        "escalate_when": ["同一区域多名同学同时断网", "账号被锁定", "持续出现明确错误码", "完成自查后仍无法连接"],
        "safety": "不要在聊天中提供密码、短信验证码或完整身份证号。",
    }


async def campus_card_handler(params: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    action = str(params.get("action", "咨询")).strip()
    guides = {
        "充值": ["使用学校官方 App、公众号或自助终端", "确认姓名与学号后选择金额", "支付完成后等待系统同步", "余额未更新时保留支付记录并联系一卡通中心"],
        "挂失": ["立即通过官方 App/自助终端挂失", "无法在线操作时携带有效证件前往一卡通中心", "挂失后按学校要求办理补卡", "找到旧卡后不要直接继续使用，先确认卡状态"],
        "补卡": ["先确认原卡已挂失", "携带有效证件前往指定窗口或自助补卡机", "按规定缴纳工本费", "领取后确认余额与身份信息是否同步"],
        "扣费": ["记录消费时间、地点和金额", "在官方渠道查询消费明细", "对异常记录截图留存", "需要退款或冲正时由一卡通中心核验处理"],
        "缴费": ["只使用学校官方缴费平台", "核对收费项目、学号和金额", "支付后保存电子票据", "状态异常时不要重复支付，先查询交易记录"],
    }
    matched = next((name for name in guides if name in action), None)
    return {
        "action": matched or action,
        "steps": guides.get(matched, ["通过学校官方一卡通或缴费平台查询对应服务", "涉及资金或身份核验时联系一卡通中心"]),
        "real_operation_performed": False,
        "notice": "本工具仅提供流程指引，不会查询余额、执行挂失、充值、退款或缴费。",
        "safety": "不要提供支付密码、验证码、完整银行卡号或完整校园卡号。",
    }


async def dorm_service_handler(params: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    issue = str(params.get("issue", "宿舍报修")).strip()
    urgent = any(k in issue for k in ["漏电", "冒烟", "火", "燃气", "大面积漏水"])
    return {
        "issue": issue,
        "urgent": urgent,
        "steps": [
            "在学校后勤报修平台选择楼栋、房间和故障类型",
            "上传清晰照片并描述故障发生时间",
            "保留报修单号，便于查询进度",
            "超过承诺时间未处理时联系宿管或后勤值班电话",
        ],
        "emergency_guidance": "如存在漏电、冒烟、火情或人身安全风险，请立即远离危险区域并联系宿管、保卫处或当地紧急服务。" if urgent else None,
        "real_ticket_created": False,
    }


def _fallback(params: Dict[str, Any], context: Optional[Dict[str, Any]], error: str) -> Dict[str, Any]:
    return {
        "fallback": True,
        "error": error,
        "guidance": "校园业务工具暂时不可用，请改用学校官方办事大厅、网络中心、一卡通中心或后勤报修渠道。",
    }


def register_campus_tools(manager: MCPToolManager) -> None:
    """向 MCPToolManager 注册 CampusMind 业务工具。"""
    manager.register(Tool(
        name="affairs_process_guide",
        description="查询学生事务办理步骤和材料清单",
        handler=affairs_process_handler,
        schema={
            "type": "object",
            "properties": {"service": {"type": "string"}},
            "required": ["service"],
        },
        cache_ttl=600.0,
        timeout_s=3.0,
        fallback=_fallback,
    ))
    manager.register(Tool(
        name="network_self_check",
        description="生成校园网、WiFi 或 VPN 自助排查步骤",
        handler=network_diagnosis_handler,
        schema={
            "type": "object",
            "properties": {
                "symptom": {"type": "string"},
                "network_type": {"type": "string"},
            },
            "required": ["symptom"],
        },
        cache_ttl=300.0,
        timeout_s=3.0,
        fallback=_fallback,
    ))
    manager.register(Tool(
        name="campus_card_guide",
        description="提供校园卡充值、挂失、补卡、异常扣费和缴费流程",
        handler=campus_card_handler,
        schema={
            "type": "object",
            "properties": {"action": {"type": "string"}},
            "required": ["action"],
        },
        cache_ttl=600.0,
        timeout_s=3.0,
        fallback=_fallback,
    ))
    manager.register(Tool(
        name="dorm_service_guide",
        description="提供宿舍报修与后勤服务指引",
        handler=dorm_service_handler,
        schema={
            "type": "object",
            "properties": {"issue": {"type": "string"}},
            "required": ["issue"],
        },
        cache_ttl=300.0,
        timeout_s=3.0,
        fallback=_fallback,
    ))


def select_tool_calls(message: str) -> List[Tuple[str, Dict[str, Any]]]:
    """根据用户消息选择需要调用的校园工具，支持复合问题并行调用。"""
    msg = (message or "").lower()
    calls: List[Tuple[str, Dict[str, Any]]] = []

    if any(k in msg for k in ["校园网", "wifi", "wi-fi", "vpn", "断网", "无法上网", "认证失败"]):
        network_type = "VPN" if "vpn" in msg else ("WiFi" if "wifi" in msg or "wi-fi" in msg else "校园网")
        calls.append(("network_self_check", {"symptom": message, "network_type": network_type}))

    if any(k in msg for k in ["校园卡", "饭卡", "充值", "挂失", "补卡", "扣费", "一卡通", "缴费"]):
        calls.append(("campus_card_guide", {"action": message}))

    if any(k in msg for k in ["在读证明", "学生证", "请假", "缓考", "奖学金", "助学金", "学籍", "盖章"]):
        calls.append(("affairs_process_guide", {"service": message}))

    if any(k in msg for k in ["宿舍", "寝室", "报修", "门禁", "空调", "停水", "停电", "漏电"]):
        calls.append(("dorm_service_guide", {"issue": message}))

    # 按工具名去重，保留首次命中。
    seen = set()
    deduped = []
    for name, params in calls:
        if name not in seen:
            seen.add(name)
            deduped.append((name, params))
    return deduped
