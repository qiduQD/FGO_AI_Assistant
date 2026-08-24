import json

from agent.core import AgentService
from agent.memory import MemoryStore
from agent.prompts import build_system_prompt


class EmptyPersona:
    def retrieve(self, query):
        return ""


def test_agent_service_finishes_and_persists_final_reply(tmp_path, monkeypatch):
    memory = MemoryStore(str(tmp_path / "s"), str(tmp_path / "p"), str(tmp_path / "a"))
    responses = iter([
        json.dumps({"persona_reply": "前辈，已经完成。", "emotion": "happy", "action": "finish", "params": {}})
    ])
    monkeypatch.setattr("agent.core.call_ollama", lambda messages, json_mode=False: next(responses))
    emotions = []
    service = AgentService(memory, EmptyPersona())

    result = service.run_agent("完成任务", on_emotion=emotions.append)

    assert result == "前辈，已经完成。"
    assert emotions == ["happy"]
    assert memory.messages[-1]["content"] == "前辈，已经完成。"


def test_agent_service_passes_structured_tool_observation(tmp_path, monkeypatch):
    memory = MemoryStore(str(tmp_path / "s"), str(tmp_path / "p"), str(tmp_path / "a"))
    captured = []
    responses = iter([
        json.dumps({"persona_reply": "正在处理。", "emotion": "neutral", "action": "finish", "params": {}})
    ])

    def fake_call(messages, json_mode=False):
        captured.append(messages)
        return next(responses)

    monkeypatch.setattr("agent.core.call_ollama", fake_call)
    service = AgentService(memory, EmptyPersona())
    service.run_agent("测试", max_steps=1)
    assert captured[0][-1]["content"] == "任务目标: 测试"


def test_agent_service_includes_consented_profile(tmp_path, monkeypatch):
    memory = MemoryStore(str(tmp_path / "s"), str(tmp_path / "p"), str(tmp_path / "a"))
    memory.add_profile("记住我偏好简洁回答")
    captured = []
    monkeypatch.setattr(
        "agent.core.call_ollama",
        lambda messages, json_mode=False: captured.append(messages) or json.dumps(
            {"persona_reply": "好的。", "action": "finish", "params": {}}
        ),
    )
    AgentService(memory, EmptyPersona()).run_agent("测试")
    assert "记住我偏好简洁回答" in captured[0][0]["content"]


def test_agent_service_executes_tool_then_finishes(tmp_path, monkeypatch):
    memory = MemoryStore(str(tmp_path / "s"), str(tmp_path / "p"), str(tmp_path / "a"))
    responses = iter([
        json.dumps({"persona_reply": "正在输入。", "action": "type_text", "params": {"text": "你好"}}),
        json.dumps({"persona_reply": "已经输入完成。", "action": "finish", "params": {}}),
    ])
    calls = []
    monkeypatch.setattr("agent.core.call_ollama", lambda messages, json_mode=False: next(responses))
    monkeypatch.setattr(
        "agent.core.execute_action_result",
        lambda action, params: calls.append((action, params)) or type("Result", (), {
            "success": True, "message": "Success: 已输入", "retryable": False,
        })(),
    )

    result = AgentService(memory, EmptyPersona()).run_agent("输入你好")

    assert result == "已经输入完成。"
    assert calls == [("type_text", {"text": "你好"})]
    assert "type_text" in build_system_prompt("agent")


def test_agent_service_does_not_repeat_identical_tool_action(tmp_path, monkeypatch):
    memory = MemoryStore(str(tmp_path / "s"), str(tmp_path / "p"), str(tmp_path / "a"))
    repeated = json.dumps({"persona_reply": "正在输入。", "action": "type_text", "params": {"text": "你好"}})
    monkeypatch.setattr("agent.core.call_ollama", lambda messages, json_mode=False: repeated)
    calls = []
    monkeypatch.setattr(
        "agent.core.execute_action_result",
        lambda action, params: calls.append((action, params)) or type("Result", (), {
            "success": True, "message": "Success: 已输入", "retryable": False,
        })(),
    )

    AgentService(memory, EmptyPersona()).run_agent("输入你好", max_steps=5)

    assert calls == [("type_text", {"text": "你好"})]
