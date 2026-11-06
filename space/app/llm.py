"""LLM sağlayıcı katmanı: lokal Ollama veya OpenAI uyumlu bulut API (Groq, Gemini vb.).

LLM_PROVIDER=ollama (varsayılan) | openai
OpenAI uyumlu mod için: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
"""
import json
import os

import httpx

PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")
BASE_URL = os.getenv("LLM_BASE_URL", "")
API_KEY = os.getenv("LLM_API_KEY", "")
REASONING = os.getenv("LLM_REASONING", "")  # örn. "low": düşünen modellerde gecikmeyi azaltır
TIMEOUT = float(os.getenv("LLM_TIMEOUT", "180"))
# GPT-5 gibi akıl yürüten modeller temperature parametresini kabul etmez: LLM_TEMPERATURE=none
TEMPERATURE = os.getenv("LLM_TEMPERATURE", "0")


def json_sohbet(sistem: str, kullanici: str, timeout: float | None = None) -> dict:
    """Modelden JSON nesnesi ister. Bozuk JSON gelirse boş sözlük döner; doğrulamayı çağıran yapar."""
    timeout = timeout or TIMEOUT
    mesajlar = [{"role": "system", "content": sistem}, {"role": "user", "content": kullanici}]
    if PROVIDER == "openai":
        govde = {"model": MODEL, "messages": mesajlar, "response_format": {"type": "json_object"}}
        if TEMPERATURE.lower() != "none":
            govde["temperature"] = float(TEMPERATURE)
        if REASONING:
            govde["reasoning_effort"] = REASONING
        r = httpx.post(f"{BASE_URL.rstrip('/')}/chat/completions", timeout=timeout,
                       headers={"Authorization": f"Bearer {API_KEY}"}, json=govde)
        r.raise_for_status()
        icerik = r.json()["choices"][0]["message"]["content"]
    else:
        r = httpx.post(f"{OLLAMA_URL}/api/chat", timeout=timeout,
                       json={"model": MODEL, "messages": mesajlar, "stream": False, "format": "json",
                             "options": {"temperature": 0, "num_predict": 350}})
        r.raise_for_status()
        icerik = r.json()["message"]["content"]
    try:
        veri = json.loads(icerik)
        return veri if isinstance(veri, dict) else {}
    except json.JSONDecodeError:
        return {}
