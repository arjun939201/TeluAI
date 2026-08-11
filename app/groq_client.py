from typing import List, Dict
import httpx

from app.config import settings


async def call_groq(system_prompt: str, history: List[Dict], user_message: str) -> str:
    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your free Groq key "
            "from https://console.groq.com"
        )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 512,
    }
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(settings.GROQ_URL, json=payload, headers=headers)

    if response.status_code != 200:
        raise RuntimeError(f"Groq API error {response.status_code}: {response.text}")

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()
