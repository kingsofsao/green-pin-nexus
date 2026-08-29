import os
from typing import Optional

import httpx
from fastapi import HTTPException

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"


async def generate_security_alert_audio(
    text: str,
    voice_id: Optional[str] = None,
) -> bytes:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="ElevenLabs is not configured. Set ELEVENLABS_API_KEY in backend/.env.",
        )

    selected_voice = voice_id or os.getenv(
        "ELEVENLABS_VOICE_ID",
        "21m00Tcm4TlvDq8ikWAM",
    )

    payload = {
        "text": text,
        "model_id": os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.75,
        },
    }

    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ELEVENLABS_API_URL}/{selected_voice}",
                json=payload,
                headers=headers,
            )

        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise HTTPException(
                status_code=502,
                detail=f"ElevenLabs request failed: {detail}",
            )

        return response.content

    except HTTPException:
        raise
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not connect to ElevenLabs: {exc}",
        )
