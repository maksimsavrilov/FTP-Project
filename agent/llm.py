from __future__ import annotations

from openai import OpenAI

from .config import settings


client = OpenAI(
    api_key=settings.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
)


def ask_llm(
    *,
    system_prompt: str,
    user_prompt: str,
) -> str:
    response = client.chat.completions.create(
        model=settings.architect_model,
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
        raise RuntimeError("LLM returned an empty response.")

    return content