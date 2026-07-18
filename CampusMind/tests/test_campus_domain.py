"""CampusMind 校园域核心逻辑测试，不调用真实 LLM、Redis 或 ChromaDB。"""
import asyncio
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import anthropic  # noqa: F401
except ModuleNotFoundError:
    anthropic = types.ModuleType("anthropic")

    class AsyncAnthropic:  # pragma: no cover - only used in minimal local envs
        def __init__(self, **kwargs):
            self.messages = types.SimpleNamespace(create=None)

    anthropic.AsyncAnthropic = AsyncAnthropic
    sys.modules["anthropic"] = anthropic

from agents.agent_orchestrator import AgentOrchestrator, AgentType, Request
from core.intent_recognizer import IntentCategory, IntentRecognizer
from core.skill_loader import SkillManager
from mcp.campus_tools import register_campus_tools, select_tool_calls
from mcp.tool_manager import MCPToolManager


def test_pattern_recognition_matches_campus_domains():
    recognizer = IntentRecognizer(api_key="test", base_url="https://example.invalid")
    assert recognizer._pattern_recognize("校园网认证失败")["intent"] == IntentCategory.NETWORK_SUPPORT
    assert recognizer._pattern_recognize("校园卡丢了需要挂失")["intent"] == IntentCategory.CAMPUS_CARD
    assert recognizer._pattern_recognize("在读证明怎么办")["intent"] == IntentCategory.STUDENT_AFFAIRS


def test_fused_vote_returns_fused_confidence():
    recognizer = IntentRecognizer(api_key="test", base_url="https://example.invalid")
    intent, confidence = recognizer._vote(
        {"intent": IntentCategory.NETWORK_SUPPORT, "confidence": 0.9},
        {"intent": IntentCategory.OTHER, "confidence": 0.0},
        {"intent": IntentCategory.NETWORK_SUPPORT, "confidence": 0.2},
    )
    assert intent == IntentCategory.NETWORK_SUPPORT
    assert confidence >= 0.79


def test_compound_message_selects_multiple_tools():
    calls = select_tool_calls("校园网认证失败，而且校园卡也充值不了")
    assert [name for name, _ in calls] == ["network_self_check", "campus_card_guide"]


def test_tool_manager_validation_cache_and_fallback():
    async def run():
        manager = MCPToolManager(api_key="test", base_url="https://example.invalid")
        register_campus_tools(manager)

        params = {"symptom": "校园网认证失败", "network_type": "校园网"}
        first = await manager.call("network_self_check", params)
        second = await manager.call("network_self_check", params)
        invalid = await manager.call("campus_card_guide", {})

        assert first.success and first.data["diagnosis_steps"]
        assert second.success and second.cached
        assert invalid.success and invalid.data["fallback"] is True

    asyncio.run(run())


def test_orchestrator_routes_and_collaborates():
    orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
    orchestrator._pool = {
        AgentType.GENERAL: [object()],
        AgentType.AFFAIRS: [object()],
        AgentType.NETWORK: [object()],
        AgentType.CAMPUS_CARD: [object()],
    }

    assert orchestrator._route(IntentCategory.CAMPUS_POLICY, None) == AgentType.AFFAIRS
    assert orchestrator._route(IntentCategory.NETWORK_SUPPORT, None) == AgentType.NETWORK

    request = Request(
        message="校园网断了，校园卡也充值失败",
        user_id="student",
        conv_id="test",
        intent=IntentCategory.NETWORK_SUPPORT,
    )
    assert orchestrator._collaboration_targets(request) == [AgentType.NETWORK, AgentType.CAMPUS_CARD]


def test_all_campus_skills_load():
    manager = SkillManager("skills")
    skills = manager.load()
    assert len(skills) == 4
    prompt = manager.prompt_for("校园网认证失败", "network")
    assert "校园网络故障排查规范" in prompt
