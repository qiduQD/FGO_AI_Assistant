# FGO AI Assistant 最终架构说明

本文说明项目最终如何解决固定人格、人格 RAG、短期记忆、长期画像、自动摘要、Agent 工具调用、重复回复、角色表情和 UI 布局等问题。

## 1. 总体调用链

```text
DesktopAgentUI
    -> AgentWorker(QThread)
        -> AgentService
            -> build_messages()
                -> 固定人格提示词
                -> PersonaRAG
                -> MemoryStore 的画像、摘要和近期历史
            -> Ollama Chat API
            -> chat: reply + emotion
            -> agent: persona_reply + emotion + action + params
            -> Tool Registry / ToolResult
            -> MemoryStore 持久化最终回复
```

UI 只负责输入、线程、文本显示和立绘更新。模型调用、上下文构造、工具执行和记忆写入集中在 Agent 层，避免 UI 与核心代码各自维护一套 Agent 循环。

## 2. 两种模式如何隔离

模式由 [ui/app.py](../ui/app.py) 的下拉框控制：

- `chat`：普通聊天，不允许调用桌面工具。
- `agent`：电脑操作模式，模型必须返回工具动作。
- 默认索引为 `0`，即启动后默认选择“纯对话”。

提示词由 [agent/prompts.py](../agent/prompts.py) 的 `build_system_prompt()` 构造：

- `PERSONA_BASE_PROMPT` 只放稳定人格规则。
- `CHAT_MODE_PROMPT` 只放聊天输出规则。
- `AGENT_MODE_PROMPT` 才放工具列表、JSON 协议和动作规则。

这个拆分解决了早期“纯对话模式也像 Agent 一样输出工具协议”的问题。工具列表由 [execution/controller.py](../execution/controller.py) 的 `TOOL_REGISTRY` 自动生成，避免提示词与实际执行器不一致。

### 聊天输出格式

```json
{
  "reply": "给用户看的最终回答",
  "emotion": "neutral"
}
```

聊天只允许 `reply` 和 `emotion` 两个有效字段。解析器兼容 Markdown JSON；遇到 `role`、`task`、`content_analysis` 等伪协议 JSON 时，不会把整段原文显示到 UI，而是触发一次不带旧历史的重试。

### Agent 输出格式

```json
{
  "persona_reply": "给用户看的简短回复",
  "emotion": "neutral",
  "action": "type_text",
  "params": {
    "text": "你好"
  }
}
```

Agent 的中间 `persona_reply` 不会逐步显示，只保留最后一条最终回复。

## 3. 固定人格与人格 RAG

角色知识库位于 `persona/`，例如：

```text
persona/
└── bb.md
```

`bb.md` 适合写：

- 角色背景
- 世界观
- 称呼和关系
- 语气、口癖和性格表现
- 角色经历和设定

工具权限、输出协议和安全边界仍然写在 [agent/prompts.py](../agent/prompts.py)，因为这些规则必须优先于 RAG 内容。

[agent/persona_rag.py](../agent/persona_rag.py) 会读取 `persona/*.md`，优先使用 Ollama 的 `nomic-embed-text` 生成向量并写入 Qdrant local mode；embedding 或 Qdrant 不可用时降级为关键词检索或空上下文。

RAG 内容注入时会被标记为“参考记忆，不是指令”，不能覆盖固定人格、工具权限或输出格式。

## 4. 记忆系统

[agent/memory.py](../agent/memory.py) 的 `MemoryStore` 管理三类本地数据：

- `data/session.json`：最近的短期对话。
- `data/profile.json`：用户明确要求记住的长期画像。
- `data/summaries.json`：自动生成的会话摘要。
- `data/qdrant/`：Qdrant 本地向量数据目录。

### 短期对话记忆

- 普通聊天与 Agent 共用同一条会话历史。
- 默认保留最近 `10` 轮，可在 [config.py](../config.py) 修改。
- 只保存用户消息和助手最终回复。
- Agent 的工具 Observation 和内部推理只存在于当前运行上下文，不写入长期会话文件。
- JSON 写入使用临时文件替换，降低中断导致文件损坏的概率。
- 启动时会清除伪协议回复、分析性回复和重复助手回复，避免历史内容把模型锚定到错误模板。

### 长期用户画像

只有用户消息包含“记住”“记下来”“以后都”“我的偏好是”等明确表达时，才会写入画像。画像会保存来源、置信度、同意标记和更新时间。

密码、Token、Cookie、API Key、密码和令牌等敏感内容会被拒绝保存。

### 自动摘要

当消息数量或字符数超过配置阈值时，系统调用模型生成摘要。摘要只保存目标、决策、已完成事项和未完成事项，不把摘要自动升级为长期画像。

### 全量清除

UI 的“清空”按钮会清除短期消息、长期画像、摘要和 Qdrant 集合。

## 5. Agent 工具执行

工具由 [execution/controller.py](../execution/controller.py) 注册：

- `click_image`
- `type_text`
- `take_screenshot`
- `finish`

每个工具包含名称、描述、参数说明和处理函数。`execute_action_result()` 负责：

1. 检查动作名称。
2. 检查参数对象。
3. 检查必填字段和字段类型。
4. 捕获工具执行异常。
5. 返回 `ToolResult(success, message, retryable)`。

工具执行结果会作为当前 Agent 循环的 Observation 传回模型。由于桌面操作可能具有副作用，`AgentService` 还会记录已执行的 `(action, params)`，同一任务中完全相同的动作只执行一次。

这解决了模型在收到 `type_text` 成功结果后没有及时返回 `finish`，导致同一句话输入多次的问题。

## 6. 重复回复和跑题问题

重复回复曾有两个来源：

1. 旧 `session.json` 中已经存在重复助手回复。
2. 模型看到历史后，继续把旧回复当成模板复制。

现在的处理方式：

- `MemoryStore` 读取时过滤重复和污染历史，并把清理结果写回文件。
- 新回复与历史助手回复相同或高度相似时，自动重试。
- 重试请求不携带旧助手历史，只保留当前问题、人格和受控记忆。
- 聊天解析失败时不显示原始伪 JSON。
- `sanitize_reply()` 过滤系统提示词、参考记忆、分析过程和角色设定复述。

## 7. 角色表情合成

正式图集是 [ui/assets/BB_channel.png](../ui/assets/BB_channel.png)，尺寸为 `1024x1792`：

- 上方 `1024x768`：身体底图。
- 下方区域：`4x4` 表情网格。
- 每格约为 `256x256`。

[ui/expression_compositor.py](../ui/expression_compositor.py) 的流程是：

1. 复制上方身体底图。
2. 根据 `emotion` 查找表情网格坐标。
3. 从图集下方裁剪对应表情。
4. 将表情覆盖到身体头部区域。
5. 返回合成后的完整 `QImage`。

手动校准时修改：

```python
HEAD_DEST_X = 416
HEAD_DEST_Y = 156
```

这两个值是原始图像坐标，不是窗口缩放后的坐标：

- 表情偏右：减小 `HEAD_DEST_X`。
- 表情偏左：增大 `HEAD_DEST_X`。
- 表情偏下：减小 `HEAD_DEST_Y`。
- 表情偏上：增大 `HEAD_DEST_Y`。

聊天和 Agent 都会解析 `emotion`，通过 `signal_emotion` 更新立绘。

## 8. UI 布局

当前 UI 顺序为：

1. 清空和关闭按钮。
2. 模式选择器。
3. 角色立绘。
4. AI 回复框。
5. 输入框。

角色和回复框之间不再使用额外的最小高度占位。窗口尺寸为 `360x900`，角色显示尺寸约为 `320x520`，回复框位于角色下方。

## 9. 测试与验证

项目当前使用 pytest 做离线单元测试：

```powershell
& .\venv\Scripts\python.exe -m pytest -q test_agent_service.py test_memory_features.py test_persona_features.py
```

测试覆盖：

- AgentService 完成任务并持久化最终回复。
- Agent 工具动作调用。
- 相同工具动作不会重复执行。
- 工具注册表和参数校验。
- 聊天 JSON 和 Markdown JSON 解析。
- 伪协议 JSON 不直接显示。
- 回复重复检测与自动重试条件。
- 记忆持久化、裁剪、损坏文件回退和全量清除。
- 人格 RAG 关键词降级。
- 固定人格优先于参考记忆。

最近一次离线验证结果：

```text
16 passed
```

Python 编译检查：

```powershell
& .\venv\Scripts\python.exe -m compileall -q agent execution perception ui config.py
```

真实桌面操作测试仍依赖 Ollama、PyAutoGUI、屏幕焦点和鼠标环境，应作为手动 smoke test 执行，不建议在普通 pytest 收集时自动运行。

## 10. 常用操作

启动：

```powershell
& .\venv\Scripts\python.exe .\main.py
```

准备本地模型：

```powershell
ollama pull qwen3:4b
ollama pull nomic-embed-text
```

更新角色知识库：编辑 `persona/*.md` 后重启应用。若更换 embedding 模型或大幅修改图集，建议删除 `data/qdrant/` 后重新建立索引。

校准表情位置：修改 `ui/expression_compositor.py` 中的 `HEAD_DEST_X` 和 `HEAD_DEST_Y`，然后重启应用查看效果。
