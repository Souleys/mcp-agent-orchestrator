"""DarkRouter provider implementation."""

from typing import List, Optional, Any, Dict, AsyncIterator
import httpx
import json
import os

from mcp_orchestrator.config import ProviderConfig
from mcp_orchestrator.providers.base import BaseProvider
from mcp_orchestrator.providers.models import (
    ModelInfo,
    ModelCapabilities,
    ChatMessage,
    ChatCompletionResult,
    ChatCompletionChoice,
    ChatCompletionUsage,
    StreamChunk,
    TokenizeResult,
    UploadResult,
    HealthCheckResult,
)


class DarkRouterProvider(BaseProvider):
    """DarkRouter provider with conversation and file management."""

    def __init__(self, config: ProviderConfig, client: Optional[httpx.Client] = None, async_client: Optional[httpx.AsyncClient] = None):
        super().__init__(config, client=client, async_client=async_client)
        self._use_x_token = True

    def _get_default_headers(self) -> Dict[str, str]:
        if self._use_x_token:
            return {
                "X-Token": self.config.api_key,
                "Content-Type": "application/json",
            }
        return super()._get_default_headers()

    def health_check(self) -> HealthCheckResult:
        import time
        start = time.time()
        try:
            # Health endpoint is at /health relative to the base URL (without /api/v1)
            health_base = self.config.base_url.replace("/api/v1", "")
            # Create a temporary client for the health check
            health_client = httpx.Client(base_url=health_base, timeout=httpx.Timeout(10.0), headers=self._get_default_headers())
            response = health_client.get("/health")
            response.raise_for_status()
            latency_ms = (time.time() - start) * 1000
            return HealthCheckResult(healthy=True, latency_ms=latency_ms, details=response.json())
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return HealthCheckResult(healthy=False, latency_ms=latency_ms, details={"error": str(e)})

    def list_models(self) -> List[ModelInfo]:
        response = self._make_request("GET", "/models")
        data = response.json()
        models = []
        for m in data.get("data", []):
            capabilities = ModelCapabilities(
                supports_streaming=True,
                supports_tools=m.get("supports_tools", False),
                supports_vision=m.get("supports_vision", False),
                max_context_tokens=m.get("max_context_tokens", 4096),
                max_output_tokens=m.get("max_output_tokens", 4096),
            )
            models.append(ModelInfo(
                id=m["id"],
                name=m.get("name", m["id"]),
                provider="darkrouter",
                capabilities=capabilities,
                description=m.get("description"),
            ))
        return models

    def chat_completion(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> ChatCompletionResult:
        msg_dicts = [{"role": m.role, "content": m.content} for m in messages]
        payload = {"model": model, "messages": msg_dicts}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        payload.update(kwargs)
        response = self._make_request("POST", "/chat/completions", json=payload)
        data = response.json()
        choices = []
        for i, choice in enumerate(data.get("choices", [])):
            msg = choice.get("message", {})
            choices.append(ChatCompletionChoice(
                index=i,
                message=ChatMessage(role=msg.get("role", "assistant"), content=msg.get("content", ""), tool_calls=msg.get("tool_calls")),
                finish_reason=choice.get("finish_reason", "stop"),
            ))
        usage = data.get("usage", {})
        return ChatCompletionResult(
            id=data.get("id", ""), model=data.get("model", model), choices=choices,
            usage=ChatCompletionUsage(prompt_tokens=usage.get("prompt_tokens", 0), completion_tokens=usage.get("completion_tokens", 0), total_tokens=usage.get("total_tokens", 0)),
            created=data.get("created", 0),
        )

    def stream_chat(self, *args, **kwargs) -> AsyncIterator[StreamChunk]:
        raise NotImplementedError

    def tokenize(self, model: str, text: str) -> TokenizeResult:
        response = self._make_request("POST", "/tokenize", json={"model": model, "text": text})
        data = response.json()
        return TokenizeResult(tokens=data.get("tokens", []), token_count=data.get("count", 0))

    def upload_file(self, file_path: str, purpose: str = "assistants") -> UploadResult:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
            data = {"purpose": purpose}
            response = self.client.post("/files", files=files, data=data)
            response.raise_for_status()
        data = response.json()
        return UploadResult(file_id=data.get("id", ""), filename=data.get("filename", os.path.basename(file_path)), bytes=data.get("bytes", 0), purpose=data.get("purpose", purpose), created_at=data.get("created_at", 0))

    def create_conversation(self, model: str, system_prompt: Optional[str] = None) -> str:
        payload = {"model": model}
        if system_prompt:
            payload["system_prompt"] = system_prompt
        response = self._make_request("POST", "/conversations", json=payload)
        return response.json().get("id", "")

    def chat_in_conversation(
        self,
        conversation_id: str,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> ChatCompletionResult:
        msg_dicts = [{"role": m.role, "content": m.content} for m in messages]
        payload = {"messages": msg_dicts}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools is not None:
            payload["tools"] = tools
        payload.update(kwargs)
        response = self._make_request("POST", f"/conversations/{conversation_id}/messages", json=payload)
        data = response.json()
        choices = []
        for i, choice in enumerate(data.get("choices", [])):
            msg = choice.get("message", {})
            choices.append(ChatCompletionChoice(
                index=i,
                message=ChatMessage(role=msg.get("role", "assistant"), content=msg.get("content", ""), tool_calls=msg.get("tool_calls")),
                finish_reason=choice.get("finish_reason", "stop"),
            ))
        usage = data.get("usage", {})
        return ChatCompletionResult(
            id=data.get("id", ""), model=data.get("model", ""), choices=choices,
            usage=ChatCompletionUsage(prompt_tokens=usage.get("prompt_tokens", 0), completion_tokens=usage.get("completion_tokens", 0), total_tokens=usage.get("total_tokens", 0)),
            created=data.get("created", 0),
        )

    def list_conversations(self) -> List[Dict[str, Any]]:
        response = self._make_request("GET", "/conversations")
        return response.json().get("data", [])

    def delete_conversation(self, conversation_id: str) -> bool:
        response = self._make_request("DELETE", f"/conversations/{conversation_id}")
        return response.status_code == 204

    def list_files(self) -> List[Dict[str, Any]]:
        response = self._make_request("GET", "/files")
        return response.json().get("data", [])

    def delete_file(self, file_id: str) -> bool:
        response = self._make_request("DELETE", f"/files/{file_id}")
        return response.status_code == 204