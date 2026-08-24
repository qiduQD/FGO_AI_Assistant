# execution/controller.py
from dataclasses import dataclass
from typing import Any, Callable

from execution.tools import take_screenshot, find_and_click, type_text


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: str
    handler: Callable[..., str]


@dataclass(frozen=True)
class ToolResult:
    success: bool
    message: str
    retryable: bool = False


TOOL_REGISTRY = {
    "click_image": ToolSpec(
        "click_image", "在屏幕上查找指定图片并点击", '{"template_path": "图片路径"}', find_and_click,
    ),
    "type_text": ToolSpec(
        "type_text", "模拟键盘输入指定文本", '{"text": "要输入的字符串"}', type_text,
    ),
    "take_screenshot": ToolSpec(
        "take_screenshot", "截取当前屏幕", "{}", take_screenshot,
    ),
    "finish": ToolSpec(
        "finish", "任务已完成或无法继续", "{}", lambda: "Success: 任务已标记为完成",
    ),
}


def tool_prompt() -> str:
    return "\n".join(
        f"{index}. {spec.name}: {spec.description}。参数: {spec.parameters}"
        for index, spec in enumerate(TOOL_REGISTRY.values(), 1)
    )


def execute_action_result(action_name: str, params: dict[str, Any]) -> ToolResult:
    if not isinstance(action_name, str) or not action_name:
        return ToolResult(False, "Error: 工具名称为空，已停止执行")
    if not isinstance(params, dict):
        return ToolResult(False, "Error: 工具参数必须是对象")
    spec = TOOL_REGISTRY.get(action_name)
    if spec is None:
        return ToolResult(False, f"Error: 未知的工具名称 '{action_name}'")
    if action_name == "click_image" and not isinstance(params.get("template_path"), str):
        return ToolResult(False, "Error: click_image 缺少 template_path 参数")
    if action_name == "type_text" and not isinstance(params.get("text"), str):
        return ToolResult(False, "Error: type_text 缺少 text 参数")
    try:
        if action_name == "click_image":
            message = spec.handler(params["template_path"])
        elif action_name == "type_text":
            message = spec.handler(params["text"])
        elif action_name == "take_screenshot":
            message = f"Success: 截图已保存至 {spec.handler()}"
        else:
            message = spec.handler()
        success = str(message).startswith("Success")
        return ToolResult(success, str(message), retryable=not success)
    except Exception as error:
        return ToolResult(False, f"Error: 工具执行失败 - {error}", retryable=True)

def execute_action(action_name: str, params: dict) -> str:
    """
    统一的工具执行入口
    :param action_name: 工具名称
    :param params: 参数字典
    """
    print(f"\n[Tool Execution] 正在执行: {action_name} | 参数: {params}")
    return execute_action_result(action_name, params).message