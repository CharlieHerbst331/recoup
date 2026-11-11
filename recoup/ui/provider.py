"""Server-side model selection for the synthetic UI (design/02 §5.9, §6)."""

import os

from recoup.app import RecoupConfig


def provider_status(config: RecoupConfig) -> dict:
    model = (config.model or os.environ.get("RECOUP_MODEL", "")).strip()
    key_configured = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    missing = []
    if not key_configured:
        missing.append("OPENAI_API_KEY")
    if not model:
        missing.append("RECOUP_MODEL")
    return {
        "mode": config.llm,
        "model": model or None,
        "key_configured": key_configured,
        "available": not missing,
        "missing": missing,
    }


def select_provider(config: RecoupConfig, payload: dict) -> RecoupConfig:
    if set(payload) - {"mode", "case_id"}:
        raise ValueError("Set credentials in the server environment, not in the browser.")
    mode = payload.get("mode")
    if mode not in ("fake", "live"):
        raise ValueError("Choose fake or live LLM mode.")
    if mode == "live":
        status = provider_status(config)
        if status["missing"]:
            raise ValueError("Set " + " and ".join(status["missing"]) + " on the server first.")
    return config.model_copy(update={"llm": mode})
