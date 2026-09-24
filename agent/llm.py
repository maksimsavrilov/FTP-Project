from __future__ import annotations

import time
from threading import Lock

from openai import OpenAI

from .config import Config


class RateLimiter:
    def __init__(self, requests_per_minute: int) -> None:
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be > 0")

        self.interval = 60.0 / requests_per_minute
        self._lock = Lock()
        self._last_request = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self.interval - (now - self._last_request)

            if delay > 0:
                time.sleep(delay)

            self._last_request = time.monotonic()


class OpenRouterLLM:
    def __init__(self, config: Config) -> None:
        self.client = OpenAI(
            api_key=config.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        self.model = config.openrouter_model

        self.rate_limiter = RateLimiter(
            config.requests_per_minute
        )

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        self.rate_limiter.wait()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            temperature=0,
        )

        content = response.choices[0].message.content

        if not content:
            raise RuntimeError("LLM returned empty response")

        return content