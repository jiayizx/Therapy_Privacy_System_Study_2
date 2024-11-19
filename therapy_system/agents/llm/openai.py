import os
from openai import OpenAI

from therapy_system.agents.llm import LM_Agent
from typing import Generator

GPT_MODELS_MAPPING = {
    "GPT-4o-mini": "gpt-4o-mini",
    "GPT-3.5-turbo": "gpt-3.5-turbo",
    "GPT-4o": "gpt-4o-2024-08-06",
}

class OpenAIAgent(LM_Agent):
    def __init__(
        self,
        engine,
        temperature=0.7,
        max_tokens=400,
        stream=False,
    ):
        if engine in GPT_MODELS_MAPPING:
            engine = GPT_MODELS_MAPPING[engine]
        super().__init__(engine, temperature, max_tokens, stream)
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    def _chat(self, messages) -> str:
        chat = self.client.chat.completions.create(
            model=self.engine,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return chat.choices[0].message.content
    
    def _chat_with_stream(self, messages) -> Generator[str, None, None]:
        chat = self.client.chat.completions.create(
            model=self.engine,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )
        for chunk in chat:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content