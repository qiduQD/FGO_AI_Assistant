# test_step2.py
from execution.controller import execute_action
from execution.tools import take_screenshot

# 1. 先截一张屏幕图
print("1. 测试屏幕截图...")
res1 = take_screenshot()
print(res1)

# 2. 测试文本输入工具
print("\n2. 测试剪贴板粘贴文本（请确保光标在可输入位置，3秒后执行）...")
import time
time.sleep(3)
res2 = execute_action("type_text", {"text": "Hello Agent!"})
print(res2)