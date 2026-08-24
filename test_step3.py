# test_step3.py
from agent.core import run_agent

if __name__ == "__main__":
    # 测试指令：让 Agent 输入一段文本
    user_input = "请在当前光标位置帮我输入文本 'Agent Demo Complete!'"
    
    print("请在 3 秒内将鼠标光标点进任何可输入的文本框（如记事本/浏览器搜索框）...")
    import time
    time.sleep(3)
    
    # 启动 Agent
    run_agent(user_input)