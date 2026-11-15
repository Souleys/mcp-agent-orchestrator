"""Base provider protocol and implementation."""

from abc import abstractmethod
from typing import AsyncIterator, List, Optional, Any, Dict, Protocol
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from mcp_orchestrator.config import ProviderConfig
from mcp_orchestrator.providers.models import (
    ModelInfo,
    ChatMessage,
    ChatCompletionResult,
    StreamChunk,
    TokenizeResult,
    UploadResult,
    HealthCheckResult,
)


class Provider(Protocol):
    """Protocol defining the interface for all model providers."""

    @abstractmethod
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
        """Send a chat completion request."""
        ...

    @abstractmethod
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
        """Stream a chat completion."""
        ...

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """List available models from the provider."""
        ...

    @abstractmethod
    def tokenize(self, model: str, text: str) -> TokenizeResult:
        """Tokenize text for a specific model."""
        ...

    @abstractmethod
    def upload_file(self, file_path: str, purpose: str = "assistants") -> UploadResult:
        """Upload a file to the provider."""
        ...

    @abstractmethod
    def health_check(self) -> HealthCheckResult:
        """Check provider health."""
        ...


def _is_retryable_error(exc: BaseException) -> bool:
    """Check if an exception is retryable."""
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        # Retry on 5xx server errors
        return exc.response.status_code >= 500
    return False


class BaseProvider:
    """Base provider with common HTTP client, retry logic, and timeout handling."""

    def __init__(self, config: ProviderConfig, client: Optional[httpx.Client] = None, async_client: Optional[httpx.AsyncClient] = None):
        self.config = config
        self._client = client
        self._async_client = async_client

    @property
    def client(self) -> httpx.Client:
        """Get or create synchronous HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(self.config.timeout or 30.0),
                headers=self._get_default_headers(),
            )
        return self._client

    @property
    def async_client(self) -> httpx.AsyncClient:
        """Get or create asynchronous HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(self.config.timeout or 30.0),
                headers=self._get_default_headers(),
            )
        return self._async_client

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for requests."""
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _make_request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        max_retries = self.config.max_retries or 3

        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(_is_retryable_error),
            reraise=True,
        )
        def _request() -> httpx.Response:
            response = self.client.request(method, path, **kwargs)
            response.raise_for_status()
            return response

        return _request()

    async def _make_async_request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make async HTTP request with retry logic."""
        max_retries = self.config.max_retries or 3

        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(_is_retryable_error),
            reraise=True,
        )
        async def _request() -> httpx.Response:
            response = await self.async_client.request(method, path, **kwargs)
            response.raise_for_status()
            return response

        return await _request()

    def close(self) -> None:
        """Close synchronous HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    async def aclose(self) -> None:
        """Close asynchronous HTTP client."""
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None

    def __enter__(self) -> "BaseProvider":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    async def __aenter__(self) -> "BaseProvider":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()

    # Abstract methods that subclasses must implement
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
        raise NotImplementedError

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

    def list_models(self) -> List[ModelInfo]:
        raise NotImplementedError

    def tokenize(self, model: str, text: str) -> TokenizeResult:
        raise NotImplementedError

    def upload_file(self, file_path: str, purpose: str = "assistants") -> UploadResult:
        raise NotImplementedError

    def health_check(self) -> HealthCheckResult:
        raise NotImplementedError