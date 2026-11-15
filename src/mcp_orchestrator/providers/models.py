"""Pydantic models for provider abstraction layer."""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class ModelCapabilities(BaseModel):
    """Capabilities of a model."""
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_vision: bool = False
    supports_audio: bool = False
    max_context_tokens: int = 4096
    max_output_tokens: int = 4096


class ModelInfo(BaseModel):
    """Information about a model."""
    id: str
    name: str
    provider: str
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)
    description: Optional[str] = None
    pricing: Optional[Dict[str, float]] = None


class ChatMessage(BaseModel):
    """A chat message."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionChoice(BaseModel):
    """A single completion choice."""
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionUsage(BaseModel):
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResult(BaseModel):
    """Result of a chat completion."""
    id: str
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage
    created: int
    object: str = "chat.completion"


class StreamChunk(BaseModel):
    """A single chunk in a streaming response."""
    id: str
    model: str
    choices: List[Dict[str, Any]]
    created: int
    object: str = "chat.completion.chunk"


class TokenizeResult(BaseModel):
    """Result of tokenization."""
    tokens: List[int]
    token_count: int


class UploadResult(BaseModel):
    """Result of file upload."""
    file_id: str
    filename: str
    bytes: int
    purpose: str
    created_at: int


class HealthCheckResult(BaseModel):
    """Result of health check."""
    healthy: bool
    latency_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
