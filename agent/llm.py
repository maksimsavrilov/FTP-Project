from __future__ import annotations

import random
import threading
import time
from xml.parsers.expat import model

from openai import OpenAI, RateLimitError

from .config import settings


class RateLimiter:
    def __init__(self, requests_per_minute: int) -> None:
        if requests_per_minute <= 0:
            raise ValueError(
                "requests_per_minute must be greater than zero."
            )

        self.interval = 60.0 / requests_per_minute
        self._lock = threading.Lock()
        self._last_request = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()

            delay = (
                self.interval
                - (now - self._last_request)
            )

            if delay > 0:
                time.sleep(delay)

            self._last_request = time.monotonic()


client = OpenAI(
    api_key=settings.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
)

rate_limiter = RateLimiter(
    settings.requests_per_minute,
)


def ask_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    max_tokens: int | None = None,
    max_retries: int = 5,
) -> str:
    for attempt in range(max_retries):
        rate_limiter.wait()

        try:
            response = client.chat.completions.create(
                model=model or settings.architect_model,
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
                max_tokens=max_tokens or settings.architect_max_tokens,
            )
            content = response.choices[0].message.content
            if not content:
                raise RuntimeError(
                    "LLM returned an empty response."
                )
            return content
        
        except RateLimitError:
            if attempt == max_retries - 1:
                raise

            delay = 2 ** attempt + random.uniform(0, 1)
            print(
                f"Rate limit exceeded. Retrying in {delay:.2f} seconds..."
            )
            time.sleep(delay)

