# ElevenLabs Voice Security Alert

The Response Center now has a **Play Voice Alert** button.

The flow is:

Response Center -> FastAPI `/api/security-alert/voice` -> ElevenLabs -> MP3 -> Browser audio.

## Configure

In `backend/.env`:

```env
ELEVENLABS_API_KEY=YOUR_ACTUAL_KEY
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
```

Never put the API key in the React frontend or commit `backend/.env`.

## Run backend

```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

## Run frontend

```powershell
cd frontend
npm install
npm run dev
```
