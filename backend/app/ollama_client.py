import json
import urllib.error
import urllib.request

from .config import get_settings


class OllamaError(RuntimeError):
    pass


def generate_with_ollama(prompt: str) -> str:
    settings = get_settings()
    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_ctx": 4096,
            "num_predict": 512,
        },
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise OllamaError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise OllamaError(
            "Could not connect to Ollama. Start Ollama, then run "
            "`ollama pull qwen3:8b`."
        ) from exc
    except TimeoutError as exc:
        raise OllamaError("Ollama took too long to answer. Try a smaller model.") from exc

    answer = data.get("response", "").strip()
    if not answer:
        raise OllamaError("Ollama returned an empty response.")
    return answer
