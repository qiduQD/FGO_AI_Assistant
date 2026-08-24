# test_step1.py
from perception.llm_client import call_ollama

messages = [
    {"role": "system", "content": "你是一个助手，请严格输出 JSON，格式为: {\"reply\": \"你的回答\"}"},
    {"role": "user", "content": "你好，请自我介绍一下。"}
]

print("正在测试本地 Ollama 调用...")
response = call_ollama(messages)
print("模型返回原始结果：")
print(response)