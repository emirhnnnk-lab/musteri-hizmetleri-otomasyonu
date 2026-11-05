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


def json_sohbet(sistem: str, kullanici: str, timeout: float = 180) -> dict:
    """Modelden JSON nesnesi ister. Bozuk JSON gelirse boş sözlük döner; doğrulamayı çağıran yapar."""
    mesajlar = [{"role": "system", "content": sistem}, {"role": "user", "content": kullanici}]
    if PROVIDER == "openai":
        r = httpx.post(f"{BASE_URL.rstrip('/')}/chat/completions", timeout=timeout,
                       headers={"Authorization": f"Bearer {API_KEY}"},
                       json={"model": MODEL, "messages": mesajlar, "temperature": 0,
                             "response_format": {"type": "json_object"}})
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
