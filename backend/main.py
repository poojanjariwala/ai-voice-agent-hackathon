import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend.database import (
    create_business_record,
    create_call_record,
    get_all_businesses,
    get_business_record,
    get_system_analytics,
    increment_call_count,
    save_conversation,
)
from backend.doc_processor import clean_and_chunk, extract_text
from backend.llm_service import CONVERSATIONS, get_agent_response
from backend.voice_service import AUDIO_DIR, synthesize_speech

load_dotenv()

# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create audio directory
Path(AUDIO_DIR).mkdir(exist_ok=True)

# FASTAPI APP
app = FastAPI(
    title="AI Voice Agent",
    description="Scalable AI voice agent for business customer care",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# STATIC FILES
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

# CONFIG
VONAGE_PHONE_NUMBER = os.getenv("VONAGE_PHONE_NUMBER", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")

# IN-MEMORY STORAGE FOR CALL SESSIONS
CALL_SESSIONS = {}

VALID_LANGUAGES = ("hi", "gu", "en")


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/business", tags=["Business"])
async def create_business(
    name: str = Form(...),
    language: str = Form(...),
    file: UploadFile = None,
    db: Session = Depends(get_db),
):
    """Register a new business with knowledge document"""
    logger.info(f"Creating business: {name} (language: {language})")

    # Validation
    if language not in VALID_LANGUAGES:
        logger.error(f"Invalid language: {language}")
        raise HTTPException(400, "Language must be 'hi', 'gu', or 'en'")

    if not file:
        logger.error("No file provided")
        raise HTTPException(400, "Please upload a knowledge document")

    if not name or len(name.strip()) == 0:
        logger.error("No business name provided")
        raise HTTPException(400, "Business name cannot be empty")

    try:
        # Extract text from file
        logger.info(f"Extracting text from: {file.filename}")
        file_bytes = await file.read()
        raw_text = extract_text(file.filename, file_bytes)

        if not raw_text or len(raw_text.strip()) == 0:
            logger.error("Extracted text is empty")
            raise ValueError("The document appears to be empty")

        # Clean and chunk text
        knowledge_base = clean_and_chunk(raw_text)
        logger.info(f"Knowledge base created: {len(knowledge_base)} characters")

        # Create business in database
        business_id = str(uuid.uuid4())[:8]
        create_business_record(db, business_id, name, language, knowledge_base)

        webhook_url = f"{PUBLIC_BASE_URL}/voice/answer/{business_id}"
        logger.info(f"Business created: {business_id} - {name}")

        return {
            "success": True,
            "business_id": business_id,
            "name": name,
            "language": language,
            "voice_webhook_url": webhook_url,
            "knowledge_preview": knowledge_base[:200] + "...",
            "message": "Business registered! Copy the webhook URL into Vonage.",
        }

    except ValueError as e:
        logger.error(f"Document processing error: {str(e)}")
        raise HTTPException(400, f"Document error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(500, "An unexpected error occurred")


@app.get("/api/business/{business_id}", tags=["Business"])
async def get_business(business_id: str, db: Session = Depends(get_db)):
    """Get business details"""
    business = get_business_record(db, business_id)
    if not business:
        raise HTTPException(404, "Business not found")

    return {
        "id": business.id,
        "name": business.name,
        "language": business.language,
        "created_at": business.created_at.isoformat(),
        "total_calls": business.total_calls,
        "knowledge_base_size": len(business.knowledge_base),
    }


@app.get("/api/businesses", tags=["Business"])
async def list_businesses(db: Session = Depends(get_db)):
    """List all registered businesses"""
    businesses = get_all_businesses(db)
    return {
        "total": len(businesses),
        "businesses": [
            {
                "id": b.id,
                "name": b.name,
                "language": b.language,
                "created_at": b.created_at.isoformat(),
                "total_calls": b.total_calls,
            }
            for b in businesses
        ],
    }


@app.get("/api/analytics/overview", tags=["Analytics"])
async def get_analytics(db: Session = Depends(get_db)):
    """Get system-wide analytics"""
    return get_system_analytics(db)


# ============================================================================
# VONAGE VOICE WEBHOOKS
# ============================================================================

@app.api_route("/voice/answer/{business_id}", methods=["GET", "POST"], tags=["Voice"])
async def voice_answer(business_id: str, request: Request, db: Session = Depends(get_db)):
    """Vonage calls this when a customer calls. Returns the NCCO call flow."""
    logger.info(f"Voice answer for: {business_id}")

    business = get_business_record(db, business_id)
    if not business:
        logger.error(f"Business not found: {business_id}")
        return Response(content="[]", media_type="application/json")

    # Greetings in 3 languages
    greetings = {
        "hi": f"नमस्ते! आप {business.name} से बात कर रहे हैं। कृपया अपना सवाल बताएं।",
        "gu": f"નમસ્તે! તમે {business.name} સાથે વાત કરી રહ્યા છો. કૃપા કરીને તમારો પ્રશ્ન કહો.",
        "en": f"Hello! You've reached {business.name}. Please tell us your question.",
    }

    greeting = greetings.get(business.language, greetings["en"])

    # Return NCCO (Vonage voice instruction)
    ncco = [
        {
            "action": "talk",
            "text": greeting,
            "language": "en-US",
        },
        {
            "action": "input",
            "type": ["speech"],
            "speech": {
                "language": "en-US",
                "endOnSilence": 1.5,
            },
            "eventUrl": [f"{PUBLIC_BASE_URL}/voice/event/{business_id}"],
            "eventMethod": "POST",
        },
    ]

    # Track the call session so speech events map to the right business/call
    call_id = str(uuid.uuid4())[:8]
    CALL_SESSIONS[business_id] = call_id
    CONVERSATIONS[call_id] = []
    create_call_record(db, call_id, business_id, "")

    increment_call_count(db, business_id)
    logger.info(f"Greeting played for {business_id} (call {call_id})")

    return Response(content=json.dumps(ncco), media_type="application/json")


@app.post("/voice/event/{business_id}", tags=["Voice"])
async def voice_event(business_id: str, request: Request, db: Session = Depends(get_db)):
    """Vonage sends speech recognition results here."""
    logger.info(f"Voice event for: {business_id}")

    business = get_business_record(db, business_id)
    if not business:
        logger.error(f"Business not found: {business_id}")
        return {"status": "error"}

    # Parse the real Vonage speech-results payload
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    speech = payload.get("speech_results") or payload.get("speech", {}).get("results") or []
    customer_query = " ".join(
        r.get("text", "") for r in speech if isinstance(r, dict)
    ).strip()

    call_id = CALL_SESSIONS.get(business_id)
    history = CONVERSATIONS.get(call_id, [])

    if not customer_query:
        logger.warning("No speech result in payload; prompting caller to repeat")
        ncco = [{
            "action": "talk",
            "text": "Sorry, I did not hear that. Please try again.",
        }]
        return Response(content=json.dumps(ncco), media_type="application/json")

    logger.info(f"Caller said: {customer_query}")

    # Get response from Claude
    response_text = get_agent_response(
        business_name=business.name,
        knowledge_base=business.knowledge_base,
        language_code=business.language,
        customer_query=customer_query,
        conversation_history=history,
    )

    # Persist the exchange
    if call_id:
        save_conversation(
            db,
            conv_id=str(uuid.uuid4())[:8],
            call_id=call_id,
            user_msg=customer_query,
            agent_resp=response_text,
        )

    # Synthesize speech and return NCCO to play the response
    try:
        audio_filename = synthesize_speech(response_text, business.language)
        audio_url = f"{PUBLIC_BASE_URL}/audio/{audio_filename}"
        ncco = [{"action": "stream", "streamUrl": [audio_url]}]
    except Exception as e:
        logger.error(f"TTS failed, falling back to Vonage voice: {str(e)}")
        ncco = [{"action": "talk", "text": response_text}]

    # Listen for the next question
    ncco.append({
        "action": "input",
        "type": ["speech"],
        "speech": {
            "language": "en-US",
            "endOnSilence": 1.5,
        },
        "eventUrl": [f"{PUBLIC_BASE_URL}/voice/event/{business_id}"],
        "eventMethod": "POST",
    })

    return Response(content=json.dumps(ncco), media_type="application/json")


# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 AI Voice Agent Backend Starting...")
    logger.info(f"Public URL: {PUBLIC_BASE_URL}")
    logger.info(f"Vonage number: {VONAGE_PHONE_NUMBER or 'NOT CONFIGURED'}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
