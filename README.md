# FGO_AI_Assistant

A local-first Desktop GUI Agent using Ollama, the ReAct framework, OpenCV vision grounding, and PyQt5.

## Architecture

```text
+------------------------------+
|        PyQt5 UI Layer        |
|  (translucent desktop panel) |
+--------------+---------------+
               |
               v
+------------------------------+
|      ReAct Agent Loop        |
|   (reason -> act -> observe) |
+-------+--------------+-------+
        |              |
        v              v
+---------------+   +------------------+
| OpenCV + MSS  |   | Web Search Tool  |
| Screen Vision |   | duckduckgo_search|
+-------+-------+   +---------+--------+
        |                     |
        +----------+----------+
                   v
        +----------------------+
        |   Ollama (Local LLM) |
        +----------------------+
```

## Quick Start

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) installed and running locally

### Installation
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run
```bash
python main.py
```

## Features
- ReAct Loop for iterative local reasoning and action selection.
- OpenCV Vision Grounding for screenshot-based context understanding.
- Translucent PyQt5 UI for a lightweight desktop interaction surface.
- Web Search Tool integration using `duckduckgo_search`.
