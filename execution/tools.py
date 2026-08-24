# execution/tools.py
import cv2
import numpy as np
import mss
import pyautogui
import os
import time

# 安全设置：防止 pyautogui 鼠标失控，移动到屏幕四角可紧急停止
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

def take_screenshot(save_path: str = "temp_screenshot.png") -> str:
    """截取全屏并保存"""
    with mss.mss() as sct:
        # 截取第一个显示器
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        # 转换为 OpenCV 格式并保存
        img = np.array(sct_img)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        cv2.imwrite(save_path, img_bgr)
    return save_path

def find_and_click(template_path: str, threshold: float = 0.8) -> str:
    """
    使用 OpenCV 模板匹配在屏幕上查找目标图片并点击
    :param template_path: 目标小图路径
    :param threshold: 匹配度阈值 (0~1)
    """
    if not os.path.exists(template_path):
        return f"Error: 模板图片 {template_path} 不存在"

    # 1. 截取当前屏幕
    screen_path = take_screenshot("temp_screen_search.png")
    screen_img = cv2.imread(screen_path)
    template_img = cv2.imread(template_path)

    if template_img is None:
        return f"Error: 无法读取模板图片 {template_path}"

    # 2. OpenCV 模板匹配
    result = cv2.matchTemplate(screen_img, template_img, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # 3. 结果判断
    if max_val >= threshold:
        # 计算模板中心坐标
        h, w, _ = template_img.shape
        center_x = max_loc[0] + w // 2
        center_y = max_loc[1] + h // 2

        # 点击坐标
        pyautogui.click(center_x, center_y)
        return f"Success: 匹配成功 (相似度 {max_val:.2f})，已点击坐标 ({center_x}, {center_y})"
    else:
        return f"Failed: 未在屏幕上找到目标 {template_path}，最高相似度仅 {max_val:.2f}"

def type_text(text: str) -> str:
    """自动模拟键盘输入字符串"""
    try:
        # 使用 pyautogui 或 clipboard 处理中文输入
        import pyperclip
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        return f"Success: 已成功输入文本 '{text}'"
    except Exception as e:
        return f"Error: 输入失败 - {str(e)}"