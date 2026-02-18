# AI Interview Backend (FastAPI + OpenAI)

Backend service for two interview flows:

1. **Collector flow**: conversationally gathers interview setup fields (`role`, `type`, `level`, `techstack`, `amount`) and generates interview questions.
2. **Actual interview flow**: asks pre-generated questions in sequence, acknowledges responses naturally, and stores transcripts.

## Stack

- FastAPI
- OpenAI API (chat + audio transcription)
- Supabase PostgreSQL (SQLAlchemy)
- In-memory cache for active interview question sets

## Project Structure

```txt
backend/
  main.py
  requirements.txt
  .env.example
  app/
    api/
      router.py
      routes/
        collector.py
        interviews.py
        transcripts.py
        voice.py
    core/
      config.py
    db/
      base.py
      session.py
    models/
      collector_session.py
      interview.py
      interview_session.py
      transcript.py
    repositories/
      collector_repository.py
      interview_repository.py
      interview_session_repository.py
      transcript_repository.py
    schemas/
      collector.py
      interview.py
      transcript.py
    services/
      interview_flow_service.py
      openai_service.py
```

## Setup

1. Create virtual env and install deps:

```bash
pip install -r requirements.txt
```

2. Configure env:

```bash
copy .env.example .env
```

Fill `.env`:

- `OPENAI_API_KEY`
- `OPENAI_MODEL` (e.g. `gpt-4o-mini`)
- `OPENAI_TRANSCRIBE_MODEL` (e.g. `gpt-4o-mini-transcribe`)
- `OPENAI_TTS_MODEL` (e.g. `gpt-4o-mini-tts`)
- `OPENAI_TTS_VOICE` (e.g. `alloy`)
- `OPENAI_TTS_FORMAT` (e.g. `mp3`)
- `DATABASE_URL` (Supabase Postgres SQLAlchemy URL)

Example:

```env
DATABASE_URL=postgresql+psycopg2://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

3. Run server:

```bash
uvicorn main:app --reload
```

## API Overview

### 1) Collector flow

- `POST /api/collector/start`
- `POST /api/collector/{collector_session_id}/turn`

When all fields are collected, an interview is generated and returned as `interview_id`.

### 2) Dashboard interview listing

- `GET /api/interviews`
- `GET /api/interviews/{interview_id}`

### 3) Actual interview flow

- `POST /api/interviews/{interview_id}/start`
- `POST /api/interviews/sessions/{interview_session_id}/turn`

### 4) Transcripts

- `GET /api/transcripts/{session_type}/{session_id}`
- `POST /api/transcripts/voice/transcribe` (multipart file upload, optional transcript persistence)

`session_type` is either `collector` or `interview`.

### 5) Voice-to-voice interview (WebSocket)

- `WS /api/interviews/sessions/{interview_session_id}/voice?user_id=<optional>`

This endpoint supports turn-based voice interview flow:

1. On connect, server sends `assistant_prompt` with first/current question text + synthesized audio.
2. Client sends either:
  - `{"type":"user_audio","audio_base64":"...","filename":"answer.webm"}`
  - `{"type":"user_text","text":"..."}` (debug fallback)
3. Server returns `assistant_turn` containing:
  - `user_text` (transcribed)
  - `assistant_text`
  - `assistant_audio_base64`
  - `status` and `question_index`

Server also persists transcript entries for both user and assistant turns.

### Interview memory cache

- The backend uses a normal in-memory cache to remember interview questions for active sessions.
- Cache is used first in interview start/turn and voice WebSocket flows, then falls back to database.
- Cache resets on server restart, while database remains the source of truth.

## End-to-End Flow

```mermaid
flowchart TD
  A[User starts collector] --> B[POST /api/collector/start]
  B --> C[AI asks role]
  C --> D[User answers]
  D --> E[POST /api/collector/{id}/turn]
  E --> F{All fields collected?}
  F -->|No| G[AI acknowledges + asks next field]
  G --> D
  F -->|Yes| H[Generate questions with OpenAI]
  H --> I[Save Interview in DB]
  I --> J[Return interview_id]

  J --> K[Dashboard lists interviews]
  K --> L[User clicks Start Interview]
  L --> M[POST /api/interviews/{interview_id}/start]
  M --> N[Create interview_session]
  N --> O[Load all pre-generated questions]

  O --> P[Connect WS /api/interviews/sessions/{session_id}/voice]
  P --> Q[AI sends assistant_prompt text + audio]
  Q --> R[User sends user_audio base64]
  R --> S[Transcribe speech to text]
  S --> T[Save user transcript]
  T --> U[AI acknowledges response + asks next question]
  U --> V[Synthesize AI speech audio]
  V --> W[Send assistant_turn text + audio]
  W --> X{More questions?}
  X -->|Yes| R
  X -->|No| Y[Mark session completed + closing message]

  T --> Z[GET /api/transcripts/{session_type}/{session_id}]
  U --> Z
```
