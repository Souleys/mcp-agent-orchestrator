"""OpenAI-compatible providers (OpenAI, Anthropic, Ollama)."""

from typing import List, Optional, Any, Dict, AsyncIterator
import httpx
import json

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


class OpenAICompatibleProvider(BaseProvider):
    """Standard OpenAI-compatible API provider."""

    def health_check(self) -> HealthCheckResult:
        import time
        start = time.time()
        try:
            response = self.client.get("/models")
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
                provider="openai_compatible",
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

    def stream_chat(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        msg_dicts = [{"role": m.role, "content": m.content} for m in messages]
        payload = {"model": model, "messages": msg_dicts, "stream": True}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        payload.update(kwargs)

        async def _stream():
            async with self.async_client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            yield StreamChunk(
                                id=data.get("id", ""),
                                model=data.get("model", model),
                                choices=data.get("choices", []),
                                created=data.get("created", 0),
                            )
                        except json.JSONDecodeError:
                            continue
        return _stream()

    def tokenize(self, model: str, text: str) -> TokenizeResult:
        # OpenAI doesn't have a tokenize endpoint, return empty
        return TokenizeResult(tokens=[], token_count=0)

    def upload_file(self, file_path: str, purpose: str = "assistants") -> UploadResult:
        import os
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
            data = {"purpose": purpose}
            response = self.client.post("/files", files=files, data=data)
            response.raise_for_status()
        data = response.json()
        return UploadResult(file_id=data.get("id", ""), filename=data.get("filename", os.path.basename(file_path)), bytes=data.get("bytes", 0), purpose=data.get("purpose", purpose), created_at=data.get("created_at", 0))


class AnthropicProvider(BaseProvider):
    """Anthropic API provider."""

    def _get_default_headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

    def health_check(self) -> HealthCheckResult:
        import time
        start = time.time()
        try:
            response = self.client.get("/models")
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
                supports_tools=True,
                supports_vision=m.get("vision", False),
                max_context_tokens=m.get("max_tokens", 4096),
                max_output_tokens=m.get("max_tokens", 4096),
            )
            models.append(ModelInfo(
                id=m["id"],
                name=m.get("display_name", m["id"]),
                provider="anthropic",
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
        # Convert messages to Anthropic format
        system = None
        anthropic_messages = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                anthropic_messages.append({"role": m.role, "content": m.content})

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens or 4096,
        }
        if system:
            payload["system"] = system
        if temperature is not None:
            payload["temperature"] = temperature
        if tools is not None:
            payload["tools"] = tools
        payload.update(kwargs)

        response = self._make_request("POST", "/messages", json=payload)
        data = response.json()

        choices = []
        for i, content in enumerate(data.get("content", [])):
            if content.get("type") == "text":
                choices.append(ChatCompletionChoice(
                    index=i,
                    message=ChatMessage(role="assistant", content=content.get("text", "")),
                    finish_reason=data.get("stop_reason", "stop"),
                ))

        usage = data.get("usage", {})
        return ChatCompletionResult(
            id=data.get("id", ""), model=data.get("model", model), choices=choices,
            usage=ChatCompletionUsage(prompt_tokens=usage.get("input_tokens", 0), completion_tokens=usage.get("output_tokens", 0), total_tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0)),
            created=0,
        )

    def stream_chat(self, *args, **kwargs) -> AsyncIterator[StreamChunk]:
        raise NotImplementedError

    def tokenize(self, model: str, text: str) -> TokenizeResult:
        return TokenizeResult(tokens=[], token_count=0)

    def upload_file(self, file_path: str, purpose: str = "assistants") -> UploadResult:
        raise NotImplementedError("Anthropic does not support file upload")


class OllamaProvider(BaseProvider):
    """Ollama local server provider (OpenAI-compatible)."""

    def health_check(self) -> HealthCheckResult:
        import time
        start = time.time()
        try:
            response = self.client.get("/api/tags")
            response.raise_for_status()
            latency_ms = (time.time() - start) * 1000
            return HealthCheckResult(healthy=True, latency_ms=latency_ms, details=response.json())
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return HealthCheckResult(healthy=False, latency_ms=latency_ms, details={"error": str(e)})

    def list_models(self) -> List[ModelInfo]:
        response = self._make_request("GET", "/api/tags")
        data = response.json()
        models = []
        for m in data.get("models", []):
            capabilities = ModelCapabilities(
                supports_streaming=True,
                supports_tools=False,
                supports_vision=False,
                max_context_tokens=4096,
                max_output_tokens=4096,
            )
            models.append(ModelInfo(
                id=m["name"],
                name=m["name"],
                provider="ollama",
                capabilities=capabilities,
                description=m.get("details", {}).get("description"),
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
        payload = {"model": model, "messages": msg_dicts, "stream": False}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["num_predict"] = max_tokens
        payload.update(kwargs)

        # Use /api/chat endpoint for Ollama
        response = self.client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

        msg = data.get("message", {})
        choices = [ChatCompletionChoice(
            index=0,
            message=ChatMessage(role=msg.get("role", "assistant"), content=msg.get("content", "")),
            finish_reason="stop",
        )]

        return ChatCompletionResult(
            id="", model=model, choices=choices,
            usage=ChatCompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            created=0,
        )

    def stream_chat(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        raise NotImplementedError

    def tokenize(self, model: str, text: str) -> TokenizeResult:
        return TokenizeResult(tokens=[], token_count=0)

    def upload_file(self, file_path: str, purpose: str = "assistants") -> UploadResult:
        raise NotImplementedError("Ollama does not support file upload")