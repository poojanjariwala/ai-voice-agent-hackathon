import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

AUDIO_DIR = "audio_files"
Path(AUDIO_DIR).mkdir(exist_ok=True)

FISH_AUDIO_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "")
FISH_AUDIO_URL = "https://api.fish.audio/v1/tts"

VOICE_MAP = {
    "hi": "1d9c9d82-5b74-4e86-b5fa-0cb3d631ca88",
    "gu": "1d9c9d82-5b74-4e86-b5fa-0cb3d631ca88",
    "en": "7a8fd6e8-8a0d-4f0a-b3f5-5f3c2c8e0d5a",
}


def download_recording(recording_url: str, auth: tuple = None) -> str:
    """Download voice recording"""
    logger.info(f"Downloading recording from: {recording_url}")

    try:
        response = requests.get(recording_url, auth=auth, timeout=30)
        response.raise_for_status()

        filename = f"{AUDIO_DIR}/recording_{os.urandom(4).hex()}.wav"
        with open(filename, "wb") as f:
            f.write(response.content)

        logger.info(f"Recording saved to: {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to download recording: {str(e)}")
        raise


def transcribe_audio(audio_path: str, language: str) -> str:
    """Transcribe audio using OpenAI Whisper"""
    logger.info(f"Transcribing audio: {audio_path} (language: {language})")

    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            logger.error("OPENAI_API_KEY not set!")
            return ""

        from openai import OpenAI

        client = OpenAI(api_key=openai_key)

        with open(audio_path, "rb") as f:
            logger.info("Calling Whisper API...")
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=language if language in ("hi", "gu", "en") else "en",
            )

        text = result.text.strip()

        if not text:
            logger.warning("Empty transcription received")
            return ""

        logger.info(f"✅ Transcribed: {text}")
        return text

    except Exception as e:
        logger.error(f"❌ Transcription failed: {str(e)}")
        return ""


def synthesize_speech(text: str, language: str) -> str:
    """Convert text to speech using Fish Audio"""
    logger.info(f"Synthesizing speech ({language}): {text[:50]}...")

    if not FISH_AUDIO_API_KEY:
        logger.error("❌ FISH_AUDIO_API_KEY not configured!")
        raise ValueError("Fish Audio API key not set")

    if not text or len(text.strip()) == 0:
        logger.error("❌ Empty text provided")
        raise ValueError("Text cannot be empty")

    try:
        voice_id = VOICE_MAP.get(language, VOICE_MAP["en"])
        logger.info(f"Using voice: {voice_id}")

        headers = {
            "Authorization": f"Bearer {FISH_AUDIO_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "text": text,
            "reference_id": voice_id,
            "normalize": True,
        }

        logger.info("Calling Fish Audio API...")
        response = requests.post(
            FISH_AUDIO_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        if not response.content:
            logger.error("❌ Empty response from Fish Audio")
            raise ValueError("Fish Audio returned empty response")

        filename = f"tts_{os.urandom(4).hex()}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(response.content)

        file_size = os.path.getsize(filepath)
        logger.info(f"✅ Audio saved: {filename} ({file_size} bytes)")

        return filename

    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ Fish Audio API error: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"❌ Speech synthesis failed: {str(e)}")
        raise
