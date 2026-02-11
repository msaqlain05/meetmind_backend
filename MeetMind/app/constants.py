"""Application constants"""

# HTTP Timeouts (seconds)
HTTP_TIMEOUT_SHORT = 10.0
HTTP_TIMEOUT_MEDIUM = 30.0
HTTP_TIMEOUT_LONG = 60.0

# Chroma Cloud API
CHROMA_API_BASE_URL = "https://api.trychroma.com"
CHROMA_API_VERSION = "v1"

# Document Types
DOC_TYPE_TRANSCRIPT = "transcript"
DOC_TYPE_SUMMARY = "summary"
DOC_TYPE_DECISION = "decision"
DOC_TYPE_ACTION_ITEM = "action_item"
DOC_TYPE_KEY_POINT = "key_point"

# LLM Models
MODEL_GPT_4O_MINI = "gpt-4o-mini"
MODEL_WHISPER = "whisper-1"
MODEL_EMBEDDING = "text-embedding-3-small"

# HTTP Connection Limits
HTTP_MAX_KEEPALIVE = 5
HTTP_MAX_CONNECTIONS = 10

# Context Snippet Settings
MAX_SNIPPET_LENGTH = 200
MAX_CONTEXT_SNIPPETS = 3
