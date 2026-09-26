# AI Voice Agent for Business Customer Care

Hackathon project: an intelligent AI-powered voice agent that provides 24/7 multilingual
customer support through Vonage phone calls.

## Features

- 🌍 Multi-language support (Hindi, Gujarati, English)
- 🤖 AI-powered responses (Claude API)
- 📞 Voice-based interface (Vonage)
- 💾 Data persistence (SQLite database)
- 🚀 Scalable architecture (FastAPI)
- 🐳 Docker containerization

## Quick Start (15 minutes)

### Prerequisites

- Python 3.10+
- API keys: Anthropic, OpenAI, Vonage, Fish Audio

### 1. Clone and set up the environment

```bash
git clone https://github.com/poojanjariwala/ai-voice-agent-hackathon.git
cd ai-voice-agent-hackathon
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### 2. Configure your API keys

```bash
cp .env.example .env
# Windows: copy .env.example .env
```

Open `.env` in VS Code and fill in your keys
(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `VONAGE_API_KEY`, `VONAGE_API_SECRET`,
`VONAGE_PHONE_NUMBER`, `FISH_AUDIO_API_KEY`).

### 3. Initialize the database

```bash
python -m backend.init_db
```

### 4. Start the backend

Run **from the project root** (not from inside `backend/`):

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

Check it is alive: http://localhost:8000/ → `{"status": "running", ...}`

### 5. Open the frontend

```bash
cd frontend
python -m http.server 5500
```

Then open http://localhost:5500 in your browser, register a business with any
.txt knowledge file, and copy the webhook URL it gives you into Vonage.

## Project Structure

```
backend/
  __init__.py           (package marker)
  main.py               (FastAPI application - Poojan)
  models.py             (SQLAlchemy models - Hardik)
  database.py           (Database functions - Hardik)
  init_db.py            (DB initialization script - Hardik)
  doc_processor.py      (PDF/TXT/CSV/Excel extraction - Henali)
  llm_service.py        (Claude AI integration - Henali)
  voice_service.py      (Whisper STT + Fish Audio TTS - Henali)
  test_api.py           (API tests - Suhas)
frontend/
  index.html            (Dashboard - Kiran)
Dockerfile              (Docker deployment - Suhas)
```

## Testing

```bash
pytest backend/test_api.py -v
```

All 8 tests pass without any API keys configured.

## Docker (optional)

```bash
docker build -t ai-voice-agent:latest .
docker run -p 8000:8000 --env-file .env ai-voice-agent:latest
```

## Team & Branches

| Member  | Branch                        | Responsibility            |
|---------|-------------------------------|---------------------------|
| Poojan  | `feature/poojan-backend`      | FastAPI backend, webhooks |
| Henali  | `feature/henali-voice-services` | Docs, LLM, voice services |
| Kiran   | `feature/kiran-frontend`      | Dashboard frontend        |
| Hardik  | `feature/hardik-database`     | Database layer            |
| Suhas   | `feature/suhas-devops`        | Tests, Docker, DevOps     |

## Deviations from the original plan (and why)

1. **`vonage==4.3.0`** instead of `3.3.0` — the pinned 3.3.0 crashes on import
   with `pydantic==2.6.1` (it was written for pydantic v1). Vonage 4.x is the
   pydantic v2 rewrite. The SDK itself is not used at runtime: the voice
   webhooks return raw NCCO JSON, so no SDK client is created.
2. **Run commands start from the project root** with
   `python -m uvicorn backend.main:app` (and `python -m backend.init_db`),
   matching the Dockerfile's `backend.main:app` — the guide's
   `cd backend && uvicorn main:app` would break package imports.
3. **Claude client is lazy-initialized** so the server starts cleanly before
   API keys are configured; the model is `claude-sonnet-4-5`.
4. **`/voice/event/{business_id}` parses the real Vonage speech results**
   (the original plan hardcoded `customer_query = "Customer question"`),
   keeps per-call conversation history, and persists exchanges to the DB.
5. **`name` is optional in the form schema** so a missing business name
   returns the documented 400 instead of FastAPI's 422.
6. `init_db.py` reconfigures stdout to UTF-8 so its emoji output works on
   Windows (cp1252) consoles.

## Testing a real phone call (needs Vonage + ngrok)

1. Start ngrok: `ngrok http 8000` and copy the HTTPS URL.
2. Put that URL into `.env` as `PUBLIC_BASE_URL` and restart the backend.
3. In the Vonage dashboard, set your number's voice webhook to
   `https://YOUR_NGROK_URL/voice/answer/YOUR_BUSINESS_ID` (POST).
4. Call your Vonage number — the agent greets, listens, answers via Claude,
   and replies with Fish Audio speech.

## License

MIT License - Hackathon Edition
