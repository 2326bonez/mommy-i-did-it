"""Model Provider Layer — capability-based, never hard-locked to one vendor.

Agents request *capabilities* (REASONING, CODEGEN...), not model names.
The registry resolves capability -> provider -> model from config/env.
Phase 0 ships the OpenAI provider; Anthropic plugs in the same interface.
"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

import httpx

log = logging.getLogger("mommy.providers")


class Capability(str, Enum):
    REASONING = "reasoning"  # planning, review, requirement generation
    CODEGEN = "codegen"      # writing source files (Phase 1+)
    VISION = "vision"        # screenshot analysis (Phase 2+)


@dataclass
class ModelRequest:
    capability: Capability
    system_prompt: str
    user_prompt: str
    max_tokens: int = 2000
    temperature: float = 0.7
    json_mode: bool = False


@dataclass
class ModelResponse:
    text: str
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0


class ProviderError(Exception):
    pass


class ModelProvider(ABC):
    name: str = "base"

    @abstractmethod
    def supports(self, cap: Capability) -> bool: ...

    @abstractmethod
    def complete(self, req: ModelRequest) -> ModelResponse: ...


class OpenAIProvider(ModelProvider):
    name = "openai"

    # Model names come from config/env — NEVER hard-coded in call sites.
    MODEL_FOR_CAPABILITY = {
        Capability.REASONING: os.environ.get("OPENAI_REASONING_MODEL", "gpt-4o-mini"),
        Capability.CODEGEN: os.environ.get("OPENAI_CODEGEN_MODEL", "gpt-4o"),
        Capability.VISION: os.environ.get("OPENAI_VISION_MODEL", "gpt-4o"),
    }

    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not self.api_key:
            log.warning("OPENAI_API_KEY not set — AI features will return 503.")

    def supports(self, cap: Capability) -> bool:
        return cap in self.MODEL_FOR_CAPABILITY

    def complete(self, req: ModelRequest) -> ModelResponse:
        if not self.api_key:
            raise ProviderError(
                "AI is not configured on this deployment (no provider API key). "
                "Set OPENAI_API_KEY to enable requirement generation."
            )
        model = self.MODEL_FOR_CAPABILITY[req.capability]
        payload: dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": req.system_prompt},
                {"role": "user", "content": req.user_prompt},
            ],
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        if req.json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            resp = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=90,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            # Log status only — never response bodies (may echo prompts/keys).
            raise ProviderError(f"Provider returned HTTP {e.response.status_code}.") from e
        except httpx.HTTPError as e:
            raise ProviderError(f"Provider request failed: {type(e).__name__}.") from e
        choice = (data.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content", "") or ""
        usage = data.get("usage") or {}
        return ModelResponse(
            text=text,
            provider=self.name,
            model=model,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
        )


class ProviderRegistry:
    """Resolve capability -> provider. Phase 0: OpenAI only (BYOK-ready)."""

    def __init__(self) -> None:
        self._providers: list[ModelProvider] = [OpenAIProvider()]

    def resolve(self, capability: Capability) -> ModelProvider:
        # Future: 1) check user's BYOK key for a supporting provider,
        #        2) fall back to platform key. Phase 0: platform key only.
        for p in self._providers:
            if p.supports(capability):
                return p
        raise ProviderError(f"No provider supports capability '{capability.value}'.")


registry = ProviderRegistry()
