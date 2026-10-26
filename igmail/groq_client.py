import re

from groq import BadRequestError, Groq

from . import config

_THINK_RE = re.compile(r"<think>.*?</think>", re.S)


def client() -> Groq:
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY tanımlı değil")
    # SDK 429/5xx hatalarında retry-after'a uyarak kendisi tekrar dener
    return Groq(api_key=config.GROQ_API_KEY, max_retries=5, timeout=120)


def chat(c: Groq, model: str, messages: list, max_tokens: int = 4096) -> str:
    kwargs = dict(model=model, messages=messages, temperature=0, max_tokens=max_tokens)
    try:
        # Qwen gibi hibrit modellerde düşünme modunu kapat (hız + token tasarrufu)
        res = c.chat.completions.create(reasoning_effort="none", **kwargs)
    except BadRequestError as e:
        if "reasoning" not in str(e).lower():
            raise
        res = c.chat.completions.create(**kwargs)
    text = res.choices[0].message.content or ""
    return _THINK_RE.sub("", text).strip()
