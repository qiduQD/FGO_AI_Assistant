# agent/core.py
import json
import re
import time

from perception.llm_client import call_ollama
from agent.memory import MemoryStore
from agent.persona_rag import PersonaRAG
from agent.prompts import build_system_prompt, is_repeated_reply, parse_chat_response, sanitize_reply
from execution.controller import execute_action_result
from agent.parser import parse_json_safely


def build_messages(user_message: str, mode: str, memory: MemoryStore,
                   persona_rag: PersonaRAG | None = None,
                   include_history: bool = True) -> list[dict[str, str]]:
    persona_rag = persona_rag or PersonaRAG()
    persona_context = persona_rag.retrieve(user_message)
    profile_context = "\n".join(item["text"] for item in memory.profile[-5:])
    summary_context = "\n".join(item["text"] for item in memory.summaries[-2:])
    memory_context = f"已确认的用户偏好:\n{profile_context}\n近期摘要:\n{summary_context}"
    return [
        {"role": "system", "content": build_system_prompt(mode, persona_context, memory_context)},
        *(memory.recent_messages() if include_history else []),
        {"role": "user", "content": user_message},
    ]


def _maybe_profile(memory: MemoryStore, user_message: str) -> None:
    if re.search(r"(记住|记下来|以后都|我的偏好是)", user_message):
        memory.add_profile(user_message, source="explicit_user_request")


def record_explicit_profile(memory: MemoryStore, user_message: str) -> None:
    _maybe_profile(memory, user_message)


def _maybe_summarize(memory: MemoryStore) -> None:
    if not memory.should_summarize():
        return
    transcript = "\n".join(
        f"{item['role']}: {item['content']}" for item in memory.recent_messages()
    )
    summary = call_ollama([
        {"role": "system", "content": "请将以下对话压缩为简洁中文摘要，只保留目标、决策、已完成和未完成事项。"},
        {"role": "user", "content": transcript},
    ])
    if summary:
        memory.add_summary(summary)


def maybe_summarize(memory: MemoryStore) -> None:
    _maybe_summarize(memory)


class AgentService:
    """Agent 编排层：UI 只负责线程和展示，所有决策流程集中在这里。"""

    def __init__(self, memory: MemoryStore | None = None,
                 persona_rag: PersonaRAG | None = None):
        self.memory = memory or MemoryStore()
        self.persona_rag = persona_rag

    def chat(self, user_message: str, cancelled=None, on_emotion=None) -> str:
        _maybe_profile(self.memory, user_message)
        history = self.memory.recent_messages()
        if cancelled and cancelled():
            return ""
        raw_response = call_ollama(
            build_messages(user_message, "chat", self.memory, self.persona_rag),
            json_mode=True,
        )
        response, emotion = parse_chat_response(raw_response, user_message)
        if not response or is_repeated_reply(response, history):
            raw_response = call_ollama(
                build_messages(user_message, "chat", self.memory, self.persona_rag, include_history=False),
                json_mode=True,
            )
            response, emotion = parse_chat_response(raw_response, user_message)
        if on_emotion:
            on_emotion(emotion)
        if response:
            self.memory.add_turn(user_message, response)
            maybe_summarize(self.memory)
        return response

    def run_agent(self, user_goal: str, max_steps: int = 5,
                  cancelled=None, on_emotion=None) -> str:
        _maybe_profile(self.memory, user_goal)
        messages = build_messages(
            f"任务目标: {user_goal}", "agent", self.memory, self.persona_rag
        )
        final_reply = ""
        executed_actions = set()
        for _ in range(max_steps):
            if cancelled and cancelled():
                break
            data = parse_json_safely(call_ollama(messages, json_mode=True))
            final_reply = sanitize_reply(data.get("persona_reply", ""), user_goal) or final_reply
            if on_emotion:
                on_emotion(str(data.get("emotion", "neutral")))
            action = data.get("action", "")
            params = data.get("params", {})
            if not isinstance(action, str) or not action:
                final_reply = "模型返回了无效动作，任务已停止。"
                break
            if action == "finish":
                break
            if not isinstance(params, dict):
                final_reply = "模型返回了无效参数，任务已停止。"
                break
            action_key = (action, json.dumps(params, ensure_ascii=False, sort_keys=True))
            if action_key in executed_actions:
                final_reply = final_reply or "前辈，操作已经完成。"
                break
            result = execute_action_result(action, params)
            executed_actions.add(action_key)
            messages.extend([
                {"role": "assistant", "content": json.dumps(data, ensure_ascii=False)},
                {"role": "user", "content": f"Observation: {result.message}"},
            ])
            if not result.success and not result.retryable:
                break
        if final_reply:
            self.memory.add_turn(user_goal, final_reply)
            maybe_summarize(self.memory)
        return final_reply


def chat(user_message: str, memory: MemoryStore | None = None) -> str:
    """执行一次不调用桌面工具的普通对话。"""
    return AgentService(memory).chat(user_message)


def run_agent(user_goal: str, max_steps: int = 5, memory: MemoryStore | None = None):
    """兼容旧调用方，实际逻辑统一由 AgentService 执行。"""
    return AgentService(memory).run_agent(user_goal, max_steps)