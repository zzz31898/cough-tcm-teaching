from __future__ import annotations

import httpx

from app.config import Settings


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _endpoint(self) -> str:
        base_url = self.settings.api_base_url.rstrip("/")
        if self.settings.uses_responses_api:
            if base_url.endswith("/responses"):
                return base_url
            if base_url.endswith("/v1"):
                return f"{base_url}/responses"
            return f"{base_url}/v1/responses"
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    def _payload(self, system_prompt: str, user_prompt: str) -> dict:
        if self.settings.uses_responses_api:
            return {
                "model": self.settings.model_name,
                "instructions": system_prompt,
                "input": user_prompt,
                "text": {"format": {"type": "json_object"}},
            }
        return {
            "model": self.settings.model_name,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

    @staticmethod
    def _responses_output_text(data: dict) -> str:
        direct_output = data.get("output_text")
        if isinstance(direct_output, str) and direct_output.strip():
            return direct_output

        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    return content["text"]
        raise ValueError("Responses API did not return output_text")

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.settings.request_timeout) as client:
            response = await client.post(
                self._endpoint(),
                headers=headers,
                json=self._payload(system_prompt, user_prompt),
            )
            response.raise_for_status()
            data = response.json()
        if self.settings.uses_responses_api:
            return self._responses_output_text(data)
        return data["choices"][0]["message"]["content"]
