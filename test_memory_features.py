import json

from agent.memory import MemoryStore


def test_memory_persists_and_keeps_recent_turns(tmp_path):
    session = tmp_path / "session.json"
    store = MemoryStore(str(session), str(tmp_path / "profile.json"), str(tmp_path / "summary.json"), max_turns=2)
    store.add_turn("旧问题", "旧回答")
    store.add_turn("新问题", "新回答")
    store.add_turn("最后问题", "最后回答")

    restored = MemoryStore(str(session), str(tmp_path / "profile.json"), str(tmp_path / "summary.json"), max_turns=2)
    assert [item["content"] for item in restored.recent_messages()] == ["新问题", "新回答", "最后问题", "最后回答"]


def test_profile_requires_safe_explicit_content(tmp_path):
    store = MemoryStore(str(tmp_path / "s"), str(tmp_path / "p"), str(tmp_path / "a"))
    assert store.add_profile("记住我喜欢简洁回答")
    assert not store.add_profile("记住我的密码是 secret")
    assert len(store.profile) == 1


def test_corrupt_memory_falls_back_to_empty(tmp_path):
    path = tmp_path / "session.json"
    path.write_text("{broken", encoding="utf-8")
    store = MemoryStore(str(path), str(tmp_path / "p"), str(tmp_path / "a"))
    assert store.messages == []


def test_clear_removes_all_json_data(tmp_path):
    store = MemoryStore(str(tmp_path / "s"), str(tmp_path / "p"), str(tmp_path / "a"))
    store.add_turn("问题", "回答")
    store.add_profile("记住偏好")
    store.add_summary("摘要")
    store.clear()
    assert store.messages == []
    assert store.profile == []
    assert store.summaries == []
    assert json.loads((tmp_path / "s").read_text(encoding="utf-8")) == []


def test_repeated_assistant_reply_is_not_reused_as_context(tmp_path):
    store = MemoryStore(str(tmp_path / "s"), str(tmp_path / "p"), str(tmp_path / "a"))
    repeated = "前辈好呀～今天想和前辈一起玩点刺激的游戏吗？"
    store.add_turn("你好呀", repeated)
    store.add_turn("我考试没合格", repeated)
    store.add_turn("你为什么只会回复这一句话", repeated)
    assert all(item["content"] != repeated for item in store.recent_messages())
