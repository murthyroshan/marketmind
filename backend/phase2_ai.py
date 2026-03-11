import json
import logging
import os
import re
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("saleskpark.phase2_ai")

try:
    from groq import Groq

    _groq_available = True
except ImportError:
    _groq_available = False
    Groq = None

_groq_client = None
_api_key = os.getenv("GROQ_API_KEY", "").strip()

if _api_key and _groq_available:
    try:
        _groq_client = Groq(api_key=_api_key)
    except Exception as exc:
        logger.error("[phase2_ai] Failed to initialize Groq client: %s", exc)


def generate_json(
    *,
    feature: str,
    system_prompt: str,
    user_prompt: str,
    fallback: Dict[str, Any],
    temperature: float = 0.45,
    max_tokens: int = 700,
) -> Dict[str, Any]:
    if not _groq_client:
        return fallback

    try:
        completion = _groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        content = (completion.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content).strip()

        parsed = json.loads(content)
        if isinstance(parsed, dict):
            merged = dict(fallback)
            merged.update({k: v for k, v in parsed.items() if v not in (None, "")})
            return merged
    except Exception as exc:
        logger.warning("[phase2_ai] %s generation failed: %s", feature, exc)

    return fallback
