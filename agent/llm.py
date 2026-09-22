from dataclasses import dataclass
from openai import OpenAI

from .config import Config


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str


class OpenRouterLLM:
    def __init__(self, config: Config) -> None:
        self.config = config

        self.client = OpenAI(
            api_key=config.openrouter_api_key,
            base_url=config.base_url,
        )

    def generate(self, prompt: str) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior software architect "
                        "performing an independent architecture review."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,
        )

        message = response.choices[0].message

        if not message.content:
            raise RuntimeError("LLM returned an empty response")

        return LLMResponse(
            content=message.content,
            model=response.model,
        )