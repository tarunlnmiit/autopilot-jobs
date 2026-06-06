import time
from openai import OpenAI, RateLimitError


def chat_with_fallback(
    llm: OpenAI,
    config: dict,
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    """Call OpenRouter with automatic fallback across free models on 429."""
    primary = config.get("openrouter_model", "nvidia/nemotron-3-super-120b-a12b:free")
    fallbacks = config.get("openrouter_fallback_models", [])
    models = [primary] + [m for m in fallbacks if m != primary]

    for model in models:
        for attempt in range(2):
            try:
                resp = llm.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content or ""
            except RateLimitError:
                if attempt == 0:
                    time.sleep(3)
                    continue
                print(f"  rate-limited: {model}, trying next model...")
                break
            except Exception as e:
                print(f"  LLM error ({model}): {e}")
                break

    raise RuntimeError("All LLM models failed. Check OpenRouter quota/keys.")
