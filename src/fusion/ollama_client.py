"""
Ollama API client with retry logic and error handling.

Author: Bibliographic Data Analysis
Date: November 2025
"""

import time
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class OllamaUnavailableError(Exception):
    """Raised when Ollama is repeatedly unreachable (timeout/connection error)."""
    pass


class OllamaClient:
    """Client for interacting with Ollama API with configurable retry and timeout."""

    def __init__(
        self,
        api_url: str = "http://localhost:11434/api/generate",
        model: str = "llama3.3:70b",
        timeout_sec: int = 220,
        max_retries: int = 4,
        retry_backoff_base_sec: int = 2,
        abort_on_timeout: bool = True,
        enable_fallback: bool = True,
        fallback_model: str = "llama3.2"
    ):
        """
        Initialize Ollama client.

        Args:
            api_url: Ollama API endpoint
            model: Model name to use
            timeout_sec: Request timeout in seconds
            max_retries: Number of retry attempts
            retry_backoff_base_sec: Base seconds for exponential backoff
            abort_on_timeout: Whether to abort on repeated timeouts
            enable_fallback: Whether to enable fallback to smaller model
            fallback_model: Fallback model name
        """
        self.api_url = api_url
        self.model = model
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries
        self.retry_backoff_base_sec = retry_backoff_base_sec
        self.abort_on_timeout = abort_on_timeout
        self.enable_fallback = enable_fallback
        self.fallback_model = fallback_model

    def test_connection(self) -> bool:
        """
        Test connection to Ollama API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": "ping",
                    "stream": False,
                    "options": {"num_predict": 4}
                },
                timeout=30
            )
            if response.status_code == 200:
                logger.info(f"Ollama connected: {self.model}")
                return True
            else:
                logger.warning(f"Ollama responded with status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Ollama connection failed: {e}")
            return False

    def query(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_retries: Optional[int] = None,
        timeout_sec: Optional[int] = None,
        abort_on_timeout: Optional[bool] = None,
        num_predict: int = 180,
        temperature: float = 0.1
    ) -> Optional[str]:
        """
        Query Ollama with retry and backoff logic.

        Args:
            prompt: The prompt to send
            model: Override default model
            max_retries: Override default max retries
            timeout_sec: Override default timeout
            abort_on_timeout: Override default abort behavior
            num_predict: Number of tokens to predict
            temperature: Model temperature

        Returns:
            Response string or None if failed

        Raises:
            OllamaUnavailableError: If Ollama is unavailable after retries and abort_on_timeout is True
        """
        model = model or self.model
        max_retries = max_retries if max_retries is not None else self.max_retries
        timeout_sec = timeout_sec if timeout_sec is not None else self.timeout_sec
        abort_on_timeout = abort_on_timeout if abort_on_timeout is not None else self.abort_on_timeout

        last_err = None
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": num_predict
                        }
                    },
                    timeout=timeout_sec
                )
                if response.status_code == 200:
                    return response.json().get('response', '').strip()
                else:
                    last_err = RuntimeError(f"HTTP {response.status_code}")
                    logger.warning(
                        f"Ollama error (attempt {attempt + 1}/{max_retries}): "
                        f"Status {response.status_code}"
                    )
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_err = e
                err_type = 'Timeout' if isinstance(e, requests.exceptions.Timeout) else 'Connection error'
                logger.warning(
                    f"Ollama {err_type} (attempt {attempt + 1}/{max_retries}) - retrying..."
                )
            except Exception as e:
                last_err = e
                logger.warning(f"Unexpected Ollama error (attempt {attempt + 1}/{max_retries}): {e}")

            # Exponential backoff (2, 4, 8, ... capped at 15s)
            wait_sec = min(self.retry_backoff_base_sec * (2 ** attempt), 15)
            time.sleep(wait_sec)

        # After max_retries: either raise exception or return None
        if abort_on_timeout:
            raise OllamaUnavailableError(
                f"Ollama unavailable after {max_retries} attempts: {last_err}"
            )
        return None
