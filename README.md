# FGO AI Assistant

一个基于 PyQt5 的桌面 AI 助手，支持两种模式：
- 纯对话模式：与本地大模型进行角色化聊天。
- Agent 操作模式：按步骤执行任务并返回结果。

项目包含短期记忆、用户画像、摘要记忆和向量检索（Qdrant 本地持久化）。

## 功能特性

- 透明桌面挂件 UI（可拖动、置顶）
- 角色表情联动（基于情绪信号）
- 双模式交互：纯对话 / Agent 操作
- 多层记忆系统：
	- 会话记忆（session）
	- 用户画像（profile）
	- 摘要记忆（summaries）
	- 向量检索记忆（qdrant）
- 一键清空记忆与向量索引

## 环境要求

- Windows（当前项目主要按 Windows 方式运行）
- Python 3.10+
- 本地 Ollama 服务（默认地址见 config.py）

## 快速开始

### 1. 克隆仓库

```powershell
git clone https://github.com/qiduQD/FGO_AI_Assistant.git
cd FGO_AI_Assistant
```

### 2. 创建并激活虚拟环境

```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
```

### 3. 安装依赖

```powershell
pip install -r requirements.txt
```

### 4. 准备 Ollama

确保本地 Ollama 正在运行，并已拉取配置中的模型：
- 对话模型：`qwen3:4b`
- 向量模型：`nomic-embed-text`

可参考命令：

```powershell
ollama pull qwen3:4b
ollama pull nomic-embed-text
```

### 5. 启动应用

```powershell
python main.py
```

## 配置说明

核心配置位于 `config.py`：
- `OLLAMA_URL` / `OLLAMA_CHAT_URL` / `OLLAMA_EMBED_URL`：Ollama 接口地址
- `DEFAULT_MODEL`：默认对话模型
- `EMBEDDING_MODEL`：向量模型
- `MEMORY_*` 与 `VECTOR_*`：记忆与向量库路径和参数

如果你的模型名不同，请修改 `DEFAULT_MODEL` 与 `EMBEDDING_MODEL`。

## 运行测试

项目根目录提供了多个测试脚本：

```powershell
pytest -q
```

或按文件运行：

```powershell
pytest test_step1.py -q
pytest test_step2.py -q
pytest test_step3.py -q
```

## 项目结构

```text
agent/           # Agent 核心逻辑、解析、提示词、记忆与向量检索
perception/      # LLM 调用封装
execution/       # 执行控制器与工具层
ui/              # PyQt5 界面与角色素材
persona/         # 人设文档
data/            # 本地记忆与向量数据持久化
main.py          # 程序入口
config.py        # 全局配置
```

## 常见问题

- 启动后无回复
	- 检查 Ollama 是否运行。
	- 检查 `config.py` 中 URL 与模型名是否正确。

- UI 显示缺失角色图
	- 确认素材存在：`ui/assets/BB_channel.png`。

- 想重置记忆状态
	- 在 UI 中点击“清空”按钮。

## 免责声明

本项目为学习与实验用途，请勿在未评估风险的生产环境直接使用。
