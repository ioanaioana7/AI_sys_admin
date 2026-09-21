# ollama_client.py

import requests
from typing import List, Dict, Any
from others.agent_config import OLLAMA_BASE_URL, OLLAMA_MODEL

class OllamaError(Exception):
    pass

def ollama_chat(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Call the local Ollama /api/chat endpoint.
    NOTE: Ollama does NOT fully support OpenAI-style tool calling out of the box.
    So here we just call the model and get plain text.
    If you want real tool-calling, you need a model / server that supports it.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False
    }

    # We pass tools just in case you wrap Ollama with an OpenAI-compatible proxy.
    if tools:
        payload["tools"] = tools

    try:
        resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=60)
    except Exception as e:
        raise OllamaError(f"Could not reach Ollama at {OLLAMA_BASE_URL}: {e}")

    if resp.status_code != 200:
        raise OllamaError(f"Ollama returned status {resp.status_code}: {resp.text}")

    data = resp.json()
    # Ollama's answer is in data["message"]["content"]
    content = data.get("message", {}).get("content", "")
    return {
        "role": "assistant",
        "content": content
    }
