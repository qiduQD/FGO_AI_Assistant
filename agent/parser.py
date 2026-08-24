# agent/parser.py
import json
import re

def parse_json_safely(raw_text: str) -> dict:
    """从 LLM 返回的原始字符串中提取并解析 JSON"""
    if not raw_text:
        return {
            "persona_reply": "模型没有返回结果，请确认 Ollama 正在运行且模型名称正确。",
            "action": "finish",
            "params": {}
        }

    # 1. 尝试直接解析
    try:
        data = json.loads(raw_text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        pass

    # 2. 清理 Markdown 标记（如 ```json ... ```）
    cleaned = re.sub(r'```(?:json)?\s*|\s*```', '', raw_text).strip()
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        pass

    # 3. 用正则强行提取最外层的 { ... }
    match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            pass

    # 4. 解析失败，返回兜底 Error 结构
    return {
        "persona_reply": "切，你的指令让我的解析模块糊涂了...",
        "action": "finish",
        "params": {}
    }