import requests
import json
import base64
from config import OLLAMA_CHAT_URL, OLLAMA_EMBED_URL, DEFAULT_MODEL, EMBEDDING_MODEL

def encode_image_to_base64(image_path: str) -> str:
    """将本地图片转换为 Base64 编码字符串"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def call_ollama(messages: list, model: str = DEFAULT_MODEL, image_path: str = None,
                json_mode: bool = False) -> str:
    """
    调用 Ollama Chat API
    :param messages: 包含 context 的对话历史 [{"role": "system"/"user", "content": "..."}]
    :param model: 模型名称
    :param image_path: 可选的图片路径（用于多模态视觉识别）
    :return: 模型生成的原始字符串内容
    """
    # 如果有图片，将其注入到最新的 user message 中
    if image_path:
        base64_img = encode_image_to_base64(image_path)
        # 找到最后一个 user 消息注入图片
        for msg in reversed(messages):
            if msg["role"] == "user":
                msg["images"] = [base64_img]
                break

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,  # qwen3 默认会消耗 token 输出 thinking，导致 content 为空
        "keep_alive": "1h",
        "options": {
            "num_predict": 128,  # 强制生成的最大 Token 数，直接砍掉多余输出时间
            "temperature": 0.1   # 低随机性，推理更快更稳定
        }
    }
    if json_mode:
        payload["format"] = "json"

    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result.get("message", {}).get("content", "")
    except Exception as e:
        print(f"[LLM Client Error]: {e}")
        return ""


def embed_ollama(text: str, model: str = EMBEDDING_MODEL) -> list[float]:
    """通过 Ollama 生成文本向量；服务不可用时返回空列表。"""
    if not text.strip():
        return []
    try:
        response = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": model, "input": text},
            timeout=30,
        )
        response.raise_for_status()
        embeddings = response.json().get("embeddings", [])
        return embeddings[0] if embeddings else []
    except Exception as error:
        print(f"[Embedding Error]: {error}")
        return []