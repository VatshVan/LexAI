"""
TOKEN-OPTIMIZED CLAUDE CLIENT

Cost controls enforced here:
1. Model tiering: Haiku for cheap tasks, Sonnet for complex reasoning
2. Prompt caching: system prompts cached 1h (10x cost reduction on cache hits)
3. Output cap: Haiku<=512, Sonnet<=1024 tokens
4. Context trimming: caller must pre-trim chunks to MAX_CHUNK_TOKENS_PER_CALL

Rate limit guard:
  5 req/min across ALL models. If pipeline fires agents concurrently, we hit
  this limit. Solution: pipeline is sequential (one agent at a time).
  ClaudeClient adds 0.5s sleep after each call as a soft rate guard.
"""

import anthropic
import json
import time
import structlog
from pathlib import Path
from django.conf import settings
from pydantic import BaseModel

log = structlog.get_logger()
PROMPTS_DIR = Path(__file__).parent / "prompts"


class ClaudeClient:
    _instance = None
    _client: anthropic.Anthropic = None
    _prompts: dict[str, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = anthropic.Anthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )
            cls._instance._prompts = {
                p.stem: p.read_text()
                for p in PROMPTS_DIR.glob("*.txt")
            }
            log.info("claude_client_ready",
                     prompts_loaded=list(cls._instance._prompts.keys()))
        return cls._instance

    def _call(
        self,
        system_key: str,
        user_message: str,
        model: str,
        max_tokens: int,
    ) -> anthropic.types.Message:
        """
        Raw call with prompt caching on system prompt.
        Retries 3x on 429/529 with exponential backoff.
        Sleeps 0.5s after every successful call (rate limit guard).
        """
        system_text = self._prompts[system_key]
        attempt = 0
        while attempt < settings.CLAUDE_MAX_RETRIES:
            try:
                response = self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=settings.CLAUDE_TEMPERATURE,
                    system=[{
                        "type": "text",
                        "text": system_text,
                        "cache_control": {"type": "ephemeral"},  # 1h cache
                    }],
                    messages=[{"role": "user", "content": user_message}],
                )
                log.info("claude_call_success",
                         model=model, system_key=system_key,
                         input_tokens=response.usage.input_tokens,
                         output_tokens=response.usage.output_tokens,
                         cache_read=getattr(response.usage,
                                            "cache_read_input_tokens", 0))
                time.sleep(0.5)  # soft rate guard
                return response
            except anthropic.RateLimitError:
                wait = 2 ** attempt * 12  # 12s, 24s, 48s
                log.warning("claude_rate_limit", wait_seconds=wait)
                time.sleep(wait)
                attempt += 1
            except anthropic.OverloadedError:
                wait = 2 ** attempt * 6
                log.warning("claude_overloaded", wait_seconds=wait)
                time.sleep(wait)
                attempt += 1
        raise Exception(f"Claude call failed after {settings.CLAUDE_MAX_RETRIES} retries")

    def haiku(self, system_key: str, user_message: str) -> str:
        """Cheap call — intent, decomposition, simple tasks."""
        resp = self._call(system_key, user_message,
                          settings.CLAUDE_HAIKU_MODEL,
                          settings.CLAUDE_HAIKU_MAX_TOKENS)
        return resp.content[0].text

    def sonnet(self, system_key: str, user_message: str) -> str:
        """Powerful call — synthesis, contradiction, drafting."""
        resp = self._call(system_key, user_message,
                          settings.CLAUDE_SONNET_MODEL,
                          settings.CLAUDE_SONNET_MAX_TOKENS)
        return resp.content[0].text

    def haiku_json(self, system_key: str, user_message: str,
                   schema: type[BaseModel]) -> BaseModel:
        raw = self.haiku(system_key, user_message)
        return self._parse_json(raw, schema)

    def sonnet_json(self, system_key: str, user_message: str,
                    schema: type[BaseModel]) -> BaseModel:
        raw = self.sonnet(system_key, user_message)
        return self._parse_json(raw, schema)

    def _parse_json(self, raw: str, schema: type[BaseModel]) -> BaseModel:
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return schema.model_validate(json.loads(clean))
        except Exception as e:
            log.error("claude_json_parse_failed", raw=raw[:200], error=str(e))
            raise


def get_claude() -> ClaudeClient:
    return ClaudeClient()
