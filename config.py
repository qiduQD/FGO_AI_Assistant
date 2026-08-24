# config.py
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"

DEFAULT_MODEL = "qwen3:4b"  # 填入你本地 ollama list 里显示的准确名称
EMBEDDING_MODEL = "nomic-embed-text"

MEMORY_DIR = "data"
SESSION_MEMORY_FILE = "data/session.json"
PROFILE_MEMORY_FILE = "data/profile.json"
SUMMARY_MEMORY_FILE = "data/summaries.json"
VECTOR_DB_PATH = "data/qdrant"
VECTOR_COLLECTION = "assistant_memory"
MAX_MEMORY_TURNS = 10
SUMMARY_MESSAGE_THRESHOLD = 20
SUMMARY_CHAR_THRESHOLD = 12000
MEMORY_RETRIEVAL_LIMIT = 5
MEMORY_RETRIEVAL_MAX_CHARS = 4000