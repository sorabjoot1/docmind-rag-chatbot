"""
llm_client.py - OpenRouter LLM connection (created once, reused for every question).

The API key comes from the .env file and is never logged or sent to the browser.
"""
import logging
import threading

from langchain_openai import ChatOpenAI

import config

logger = logging.getLogger(__name__)

_llm = None
_lock = threading.Lock()


class LLMError(Exception):
    """An LLM problem with a message that is safe to show to the user."""


def is_configured():
    return bool(config.OPENROUTER_API_KEY)


def get_llm():
    global _llm
    if not is_configured():
        raise LLMError(
            "OpenRouter API key is missing. Add OPENROUTER_API_KEY to your .env file and restart the app."
        )
    if _llm is None:
        with _lock:
            if _llm is None:
                _llm = ChatOpenAI(
                    api_key=config.OPENROUTER_API_KEY,
                    base_url=config.OPENROUTER_BASE_URL,
                    model=config.LLM_MODEL,
                    temperature=config.LLM_TEMPERATURE,
                    max_tokens=config.LLM_MAX_TOKENS,
                    timeout=config.LLM_TIMEOUT_SECONDS,
                    max_retries=1,
                )
    return _llm


def _friendly_error(exc):
    text = str(exc).lower()
    if "401" in text or "invalid api key" in text or "no auth" in text or "unauthorized" in text:
        return "OpenRouter rejected the API key. Check OPENROUTER_API_KEY in your .env file."
    if "402" in text or "credit" in text:
        return "Your OpenRouter account has no credits left for this model."
    if "429" in text or "rate limit" in text:
        return "Too many requests right now. Please wait a few seconds and try again."
    if "timeout" in text or "timed out" in text:
        return "The model took too long to respond. Please try again."
    if "connect" in text or "network" in text or "resolve" in text:
        return "Could not reach OpenRouter. Check your internet connection."
    return "The language model request failed. Please try again."


def generate(messages):
    """Send messages to the LLM and return the answer text."""
    llm = get_llm()
    try:
        response = llm.invoke(messages)
    except Exception as exc:
        logger.warning("LLM request failed: %s", type(exc).__name__)  # never log details/keys
        raise LLMError(_friendly_error(exc)) from None

    content = response.content
    if isinstance(content, list):  # some models return a list of parts
        content = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return (content or "").strip()
