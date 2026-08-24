"""Local persistent short-term memory, summaries, and consented user profile."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

from config import (
    MAX_MEMORY_TURNS,
    MEMORY_DIR,
    PROFILE_MEMORY_FILE,
    SESSION_MEMORY_FILE,
    SUMMARY_CHAR_THRESHOLD,
    SUMMARY_MEMORY_FILE,
    SUMMARY_MESSAGE_THRESHOLD,
)
from agent.prompts import is_meta_reply


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    def __init__(self, session_file: str = SESSION_MEMORY_FILE,
                 profile_file: str = PROFILE_MEMORY_FILE,
                 summary_file: str = SUMMARY_MEMORY_FILE,
                 max_turns: int = MAX_MEMORY_TURNS):
        self.session_file = session_file
        self.profile_file = profile_file
        self.summary_file = summary_file
        self.max_turns = max_turns
        self.messages = self._load(session_file, [])
        cleaned_messages = self._clean_messages(self.messages)
        if cleaned_messages != self.messages:
            self.messages = cleaned_messages
            self._save(self.session_file, self.messages)
        self.profile = self._load(profile_file, [])
        self.summaries = [
            item for item in self._load(summary_file, [])
            if not is_meta_reply(item.get("text", ""))
        ]

    @staticmethod
    def _load(path: str, default: Any) -> Any:
        try:
            with open(path, "r", encoding="utf-8") as file:
                value = json.load(file)
                return value if isinstance(value, type(default)) else default
        except (OSError, json.JSONDecodeError):
            return default

    @staticmethod
    def _save(path: str, value: Any) -> None:
        directory = os.path.dirname(path) or MEMORY_DIR
        os.makedirs(directory, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix="memory-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(value, file, ensure_ascii=False, indent=2)
            os.replace(temp_path, path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def recent_messages(self) -> list[dict[str, str]]:
        return self._clean_messages(self.messages)[-self.max_turns * 2:]

    @staticmethod
    def _clean_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
        messages = [
            item for item in messages
            if not (item.get("role") == "assistant" and is_meta_reply(item.get("content", "")))
        ]
        assistant_counts = {}
        for item in messages:
            if item.get("role") == "assistant":
                content = item.get("content", "")
                assistant_counts[content] = assistant_counts.get(content, 0) + 1
        return [
            item for item in messages
            if item.get("role") != "assistant"
            or assistant_counts.get(item.get("content", ""), 0) == 1
        ]

    def add_turn(self, user: str, assistant: str) -> None:
        if is_meta_reply(assistant):
            return
        self.messages.extend([
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ])
        self.messages = self.messages[-self.max_turns * 2:]
        self._save(self.session_file, self.messages)

    def should_summarize(self) -> bool:
        return len(self.messages) >= SUMMARY_MESSAGE_THRESHOLD or sum(
            len(item.get("content", "")) for item in self.messages
        ) >= SUMMARY_CHAR_THRESHOLD

    def add_summary(self, text: str) -> None:
        if text.strip():
            self.summaries.append({"text": text.strip(), "created_at": _now()})
            self._save(self.summary_file, self.summaries)

    def add_profile(self, text: str, source: str = "user", confidence: float = 1.0) -> bool:
        lowered = text.lower()
        if not text.strip() or any(secret in lowered for secret in ("password", "token", "cookie", "api key", "密码", "令牌")):
            return False
        self.profile.append({
            "text": text.strip(), "source": source, "confidence": confidence,
            "consent": True, "updated_at": _now(),
        })
        self._save(self.profile_file, self.profile)
        return True

    def clear(self) -> None:
        self.messages = []
        self.profile = []
        self.summaries = []
        for path, value in ((self.session_file, []), (self.profile_file, []), (self.summary_file, [])):
            self._save(path, value)