# Frontend Integration Guide

This document explains:

1. How the backend interview system works
2. How your frontend should connect to it (REST + WebSocket)

---

## 1) High-level architecture

There are **2 flows**:

1. **Collector flow** (setup interview)
  - Starts with readiness confirmation, then collects `role`, `interview_type`, `level`, `techstack`, `amount`
  - Handles conversational intents like repeat request, examples request, and clarification
   - Generates questions using OpenAI
   - Saves interview in DB

2. **Actual interview flow**
   - Uses already generated questions
   - AI acknowledges user response naturally
   - AI asks next question
   - Stores transcript for every turn

Voice mode is available through WebSocket:
- User sends audio
- Backend transcribes
- Backend generates AI reply text
- Backend synthesizes AI voice audio
- Frontend plays returned audio

---

## 2) Backend base URL

Local:
- `http://127.0.0.1:8000`

Production:
- your deployed domain (e.g. Vercel URL)

All REST routes are prefixed with:
- `/api`

---

## 3) Collector flow (REST)

### Step A — start collector session

**POST** `/api/collector/start`

Request body (optional):

```json
{
  "user_id": "user_123",
  "candidate_name": "Alex"
}
```

Response:

```json
{
  "collector_session_id": 1,
  "user_id": "user_123",
  "assistant_message": "Hello Alex, I’ll ask you a few quick questions so I can prepare the perfect interview for your practice. Are you ready to begin?",
  "assistant_audio_base64": "...",
  "assistant_audio_content_type": "audio/mp3",
  "expected_field": "readiness"
}
```

### Step B — send each user answer

**POST** `/api/collector/{collector_session_id}/turn`

Request body:

```json
{
  "user_id": "user_123",
  "user_message": "Backend"
}
```

Response (not completed yet):

```json
{
  "collector_session_id": 1,
  "user_id": "user_123",
  "assistant_message": "Awesome, let’s get started. Could you tell me what role you want to train for?",
  "assistant_audio_base64": "...",
  "assistant_audio_content_type": "audio/mp3",
  "expected_field": "role",
  "completed": false,
  "interview_id": null
}
```

Example conversational intent response (same expected field retained):

```json
{
  "collector_session_id": 1,
  "user_id": "user_123",
  "assistant_message": "Sure thing. Examples include frontend developer, backend developer, full stack developer, mobile developer, designer, or data analyst. Could you tell me what role you want to train for?",
  "expected_field": "role",
  "completed": false,
  "interview_id": null
}
```

Final response (completed):

```json
{
  "collector_session_id": 1,
  "user_id": "user_123",
  "assistant_message": "Perfect. I generated your interview...",
  "expected_field": null,
  "completed": true,
  "interview_id": 42
}
```

When `completed=true`, redirect user to dashboard and show interview `42`.

### Step C — optional voice-to-voice collector mode

After creating a collector session with `/api/collector/start`, you can run setup via WebSocket:

`WS /api/collector/sessions/{collector_session_id}/voice?user_id=user_123`

Server first sends:

```json
{
  "type": "assistant_prompt",
  "collector_session_id": 1,
  "status": "collecting",
  "expected_field": "readiness",
  "assistant_text": "Hello Alex ... Are you ready to begin?",
  "assistant_audio_base64": "...",
  "assistant_audio_content_type": "audio/mp3"
}
```

Client turn payloads:

```json
{"type":"user_audio","audio_base64":"...","filename":"setup.webm"}
```

or

```json
{"type":"user_text","text":"can you repeat that question"}
```

Server turn response:

```json
{
  "type": "assistant_turn",
  "collector_session_id": 1,
  "status": "collecting",
  "expected_field": "role",
  "completed": false,
  "interview_id": null,
  "user_text": "yes",
  "assistant_text": "Great, let’s start. Could you tell me what role you want to train for?",
  "assistant_audio_base64": "...",
  "assistant_audio_content_type": "audio/mp3"
}
```

---

## 4) Dashboard flow (REST)

### List interviews

**GET** `/api/interviews?user_id=user_123`

### Get interview details + questions

**GET** `/api/interviews/{interview_id}?user_id=user_123`

---

## 5) Start actual interview (REST)

### Start session

**POST** `/api/interviews/{interview_id}/start`

Request body:

```json
{
  "user_id": "user_123"
}
```

Response:

```json
{
  "interview_session_id": 100,
  "user_id": "user_123",
  "assistant_message": "Great, let’s begin. First question: ...",
  "question_index": 0
}
```

You can run interview using:
- REST turns (`/api/interviews/sessions/{id}/turn`) or
- Voice WebSocket (recommended for voice UX)

---

## 6) Voice-to-voice interview (WebSocket)

### Connect

`WS /api/interviews/sessions/{interview_session_id}/voice?user_id=user_123`

On connect, server sends an `assistant_prompt` message with text + base64 audio.

Example incoming server event:

```json
{
  "type": "assistant_prompt",
  "user_id": "user_123",
  "interview_session_id": 100,
  "status": "active",
  "question_index": 0,
  "assistant_text": "Great, let’s begin. First question: ...",
  "assistant_audio_base64": "...",
  "assistant_audio_content_type": "audio/mp3"
}
```

### Send user audio turn

Client -> server:

```json
{
  "type": "user_audio",
  "audio_base64": "<base64-webm-or-wav>",
  "filename": "answer.webm"
}
```

Server -> client:

```json
{
  "type": "assistant_turn",
  "user_id": "user_123",
  "interview_session_id": 100,
  "status": "active",
  "question_index": 1,
  "user_text": "My answer after transcription...",
  "assistant_text": "Nice explanation. Next question: ...",
  "assistant_audio_base64": "...",
  "assistant_audio_content_type": "audio/mp3"
}
```

### Debug text mode

Client -> server:

```json
{
  "type": "user_text",
  "text": "This is my answer"
}
```

### Ping/Pong

Client:

```json
{"type":"ping"}
```

Server:

```json
{"type":"pong"}
```

### Completed status

When interview ends, `status` becomes `completed` and no next question index is sent.

---

## 7) Frontend audio handling

### Recording

Use browser APIs:
- `navigator.mediaDevices.getUserMedia({ audio: true })`
- `MediaRecorder` to capture chunks
- Convert blob to base64 and send as `user_audio`

### Playback

On `assistant_prompt` or `assistant_turn`:
1. Decode `assistant_audio_base64`
2. Build blob with `assistant_audio_content_type` (usually `audio/mp3`)
3. Create object URL
4. Play via `new Audio(url).play()`

---

## 8) Transcript integration

Fetch transcript anytime:

**GET** `/api/transcripts/{session_type}/{session_id}?user_id=user_123`

- `session_type`: `collector` or `interview`
- Returns ordered list of user + assistant messages

---

## 9) Recommended frontend sequence

1. Start collector
2. Loop collector turns until `completed=true`
3. Show interview in dashboard
4. Start interview session
5. Open voice WebSocket
6. Play AI opening voice
7. Capture user voice and send each turn
8. Play AI voice responses and render transcript
9. Stop when status is `completed`

---

## 10) Production notes

- Local `.env` does not apply to Vercel automatically.
- Set all env vars in deployment platform:
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`
  - `OPENAI_TRANSCRIBE_MODEL`
  - `OPENAI_TTS_MODEL`
  - `OPENAI_TTS_VOICE`
  - `OPENAI_TTS_FORMAT`
  - `DATABASE_URL`
- Keep `DATABASE_URL` pointed to Supabase Postgres with SSL.

---

## 11) Detailed workflow: Collector flow

### State machine

```
START
  ↓
[role] → user answers "Backend"
  ↓
[interview_type] → user answers "technical"
  ↓
[level] → user answers "Senior"
  ↓
[techstack] → user answers "Python, Django, PostgreSQL"
  ↓
[amount] → user answers "10"
  ↓
COMPLETED: questions generated + interview saved
  ↓
Dashboard shows interview ID
```

### Each turn in detail

1. **Frontend state before turn**: Knows current field (`role`, `interview_type`, etc.)
2. **User input**: Speaks or types answer
3. **Frontend sends**: `POST /api/collector/{id}/turn` with `user_message` + optional `user_id`
4. **Backend processes**:
   - Normalizes value (e.g., `techstack` → list, `amount` → int)
   - Validates (e.g., amount must be 1-30)
   - If invalid, returns error message + same `expected_field`
   - If valid, saves to DB + moves to next field
5. **Response**:
   - `completed=false`: Next field name in `expected_field`, AI acknowledgement in `assistant_message`
   - `completed=true`: `interview_id` is set, final message sent
6. **Frontend updates**: Renders AI message as speech/text

### Error flow

If user enters "invalid_amount":

```json
{
  "user_message": "999"
}
```

Response:

```json
{
  "collector_session_id": 1,
  "user_id": "user_123",
  "assistant_message": "Thanks. I need a valid value for amount: Amount must be between 1 and 30.",
  "expected_field": "amount",
  "completed": false,
  "interview_id": null
}
```

Frontend shows error and keeps same field, allowing user to retry.

---

## 12) Detailed workflow: Actual interview (REST mode)

### Setup

1. Dashboard shows list of interviews (via `GET /api/interviews`)
2. User clicks "Start Interview"
3. Frontend calls `POST /api/interviews/{interview_id}/start`
4. Backend returns `interview_session_id` + opening AI message

### Turn loop

Each turn:

```
1. Frontend renders current AI question
2. User answers
3. Frontend sends: POST /api/interviews/sessions/{session_id}/turn
   {
     "user_id": "...",
     "user_message": "..."
   }
4. Backend:
   - Retrieves current question from cache (or DB)
   - Calls OpenAI to acknowledge + generate next question
   - Saves transcript
   - Increments question index
5. Response:
   {
     "assistant_message": "...",
     "status": "active",
     "question_index": 1
   }
6. Frontend renders AI response
7. If status=="completed": end interview
   else: loop to step 1
```

### Full turn example

**Turn 1 (question index 0→1)**

Request:
```json
{
  "user_id": "user_123",
  "user_message": "I have 5 years of full-stack experience with React, Node.js, and PostgreSQL."
}
```

Backend does:
1. Fetch question at index 0: "Tell me about your experience"
2. Call OpenAI with: (user_answer, current_question, next_question)
3. OpenAI returns: "Great background. Next: How would you design a scalable API?"
4. Save transcript entry: user said "I have 5 years..."
5. Save transcript entry: AI said "Great background..."
6. Increment session to index 1

Response:
```json
{
  "interview_session_id": 100,
  "user_id": "user_123",
  "assistant_message": "Great background. Next: How would you design a scalable API?",
  "status": "active",
  "question_index": 1
}
```

Frontend:
1. Show AI response to user
2. Fetch and show next question (index 1)
3. Wait for next user input

---

## 13) Detailed workflow: Voice interview (WebSocket)

### Connection sequence

```
Frontend                          Backend
   |                                 |
   |-- WS CONNECT ----------------->|
   |   /api/interviews/sessions/    |
   |   {id}/voice?user_id=...       |
   |                                 |
   |<-- assistant_prompt event ------|
   | {audio_base64, text}            |
   |                                 |
   | [Frontend plays audio]           |
   |                                 |
   |-- user_audio event ------------>|
   | {audio_base64, filename}        |
   |                                 |
   | [Backend transcribes]           |
   | [Backend calls OpenAI]          |
   | [Backend synthesizes speech]    |
   |                                 |
   |<-- assistant_turn event --------|
   | {user_text, assistant_text,    |
   |  assistant_audio_base64}        |
   |                                 |
   | [Frontend plays audio]          |
   | [Loop or end]                   |
```

### WebSocket message types

#### From server:

**assistant_prompt** (on connect):
```json
{
  "type": "assistant_prompt",
  "user_id": "user_123",
  "interview_session_id": 100,
  "status": "active",
  "question_index": 0,
  "assistant_text": "Great, let's begin. First question: Tell me about yourself.",
  "assistant_audio_base64": "SUQzBAAAAAAAI1NTUVUIGZvciBNUDMgdmVyc2lvbiAw",
  "assistant_audio_content_type": "audio/mp3"
}
```

**assistant_turn** (after user sends audio):
```json
{
  "type": "assistant_turn",
  "user_id": "user_123",
  "interview_session_id": 100,
  "status": "active",
  "question_index": 1,
  "user_text": "I'm a full-stack engineer with 7 years experience.",
  "assistant_text": "Interesting background. Tell me about a complex system you built.",
  "assistant_audio_base64": "...",
  "assistant_audio_content_type": "audio/mp3"
}
```

**completed** (final turn):
```json
{
  "type": "completed",
  "message": "Interview completed"
}
```

**error**:
```json
{
  "type": "error",
  "message": "Invalid base64 audio"
}
```

#### To server:

**user_audio**:
```json
{
  "type": "user_audio",
  "audio_base64": "//NExAAkQQp...",
  "filename": "answer.webm"
}
```

**user_text** (debug):
```json
{
  "type": "user_text",
  "text": "My answer text"
}
```

**ping**:
```json
{"type":"ping"}
```

Server responds with `{"type":"pong"}`.

### Voice turn internals

When frontend sends `user_audio`:

1. Backend decodes base64 → bytes
2. Calls OpenAI `/audio/transcriptions` with model `gpt-4o-mini-transcribe`
3. Gets back `user_text` string (e.g., "I worked at startup X for 3 years")
4. Saves transcript: `{ speaker: "user", message: user_text }`
5. Looks up current question at session index
6. Looks up next question (or None if last)
7. Calls OpenAI `/chat/completions` with:
   - `current_question`
   - `user_text` (what they said)
   - `next_question` (what to ask next)
8. Gets back `assistant_text` (naturally phrased response + next Q)
9. Calls OpenAI `/audio/speech` to get MP3 bytes
10. Base64 encodes MP3 bytes
11. Increments session index on DB
12. Saves transcript: `{ speaker: "assistant", message: assistant_text }`
13. Sends `assistant_turn` back to client with all three fields

---

## 14) Frontend implementation checklist

### Auth & user identification

- [ ] Get `user_id` from auth token or session
- [ ] Pass `user_id` in all requests/WebSocket query param

### Collector UI

- [ ] Call `/start` and display opening question
- [ ] Loop: show AI message, capture input, send turn, update next field
- [ ] On `completed=true`, redirect to dashboard with interview ID

### Dashboard

- [ ] Fetch `/api/interviews?user_id=...`
- [ ] For each interview, show role + level + created_at
- [ ] Button to start interview or view details

### Interview (REST mode)

- [ ] Call `/start` with interview ID
- [ ] Loop turns: show question, get answer, send turn, show AI response
- [ ] On `status=completed`, show final message

### Interview (Voice WebSocket mode)

- [ ] Request mic permission (`navigator.mediaDevices.getUserMedia`)
- [ ] Open WebSocket connection
- [ ] On `assistant_prompt`: decode audio, play via `new Audio()`
- [ ] Set up `MediaRecorder` to capture user voice
- [ ] On user done speaking: encode to base64, send `user_audio`
- [ ] On `assistant_turn`: decode + play audio, show transcript
- [ ] On `completed`: close WebSocket, show results

### Audio encoding/decoding

- [ ] Record as WebM or WAV (common formats)
- [ ] Decode base64 response → Blob
- [ ] Create object URL from Blob
- [ ] Play via `<audio>` or `new Audio(url).play()`

### Transcript display

- [ ] After each turn, fetch `/api/transcripts/interview/{session_id}`
- [ ] Display user + AI messages chronologically

### Error handling

- [ ] Catch WebSocket close events (network error, session timeout)
- [ ] Retry failed POST requests with exponential backoff
- [ ] Show user-friendly error messages for API errors
- [ ] Validate user input before sending (e.g., check mic permission)

---

## 15) Example: minimal TypeScript WebSocket client

```typescript
class InterviewClient {
  private ws: WebSocket | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];

  async connectVoice(sessionId: number, userId: string) {
    const baseUrl = "wss://your-domain.com"; // or ws:// local
    this.ws = new WebSocket(
      `${baseUrl}/api/interviews/sessions/${sessionId}/voice?user_id=${userId}`
    );

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "assistant_prompt" || msg.type === "assistant_turn") {
        this.playAudio(msg.assistant_audio_base64, msg.assistant_audio_content_type);
        console.log("AI:", msg.assistant_text);
      } else if (msg.type === "completed") {
        console.log("Interview completed");
        this.ws?.close();
      } else if (msg.type === "error") {
        console.error("Server error:", msg.message);
      }
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }

  async startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.mediaRecorder = new MediaRecorder(stream);
    this.audioChunks = [];

    this.mediaRecorder.ondataavailable = (event) => {
      this.audioChunks.push(event.data);
    };

    this.mediaRecorder.onstop = () => {
      const blob = new Blob(this.audioChunks, { type: "audio/webm" });
      this.sendAudioTurn(blob);
    };

    this.mediaRecorder.start();
  }

  stopRecording() {
    this.mediaRecorder?.stop();
  }

  private async sendAudioTurn(blob: Blob) {
    const base64 = await this.blobToBase64(blob);
    const payload = {
      type: "user_audio",
      audio_base64: base64.split(",")[1],
      filename: "answer.webm"
    };
    this.ws?.send(JSON.stringify(payload));
  }

  private playAudio(base64: string, contentType: string) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    const blob = new Blob([bytes], { type: contentType });
    const url = URL.createObjectURL(blob);
    new Audio(url).play();
  }

  private blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result as string);
      reader.readAsDataURL(blob);
    });
  }
}

// Usage:
const client = new InterviewClient();
await client.connectVoice(100, "user_123");
// When user wants to speak:
await client.startRecording();
// When done:
client.stopRecording();
```

---

## 16) Transcript API usage

### Fetch all turns from an interview session

```bash
GET /api/transcripts/interview/{session_id}?user_id=user_123
```

Response:
```json
{
  "user_id": "user_123",
  "items": [
    {
      "id": 1,
      "session_type": "interview",
      "session_id": 100,
      "user_id": "user_123",
      "speaker": "assistant",
      "message": "Great, let's begin. First question: Tell me about yourself.",
      "created_at": "2026-02-18T18:00:00Z"
    },
    {
      "id": 2,
      "session_type": "interview",
      "session_id": 100,
      "user_id": "user_123",
      "speaker": "user",
      "message": "I'm a full-stack engineer with 7 years experience.",
      "created_at": "2026-02-18T18:00:05Z"
    },
    {
      "id": 3,
      "session_type": "interview",
      "session_id": 100,
      "user_id": "user_123",
      "speaker": "assistant",
      "message": "Interesting. Tell me about a complex system you built.",
      "created_at": "2026-02-18T18:00:06Z"
    }
  ]
}
```

Frontend can display this as a live chat-like UI as turns happen.

---

## 17) Caching behavior

Backend uses **in-memory cache** for interview questions:

- When interview is generated, questions are cached in memory (TTL: 2 hours)
- When interview session starts, questions are cached again (fast lookups)
- Cache is cleared when interview completes
- Database is source of truth; cache is optimization only

**Frontend implication**: No caching needed on frontend; backend handles it.

---

## 18) Rate limiting & best practices

- Don't call `/api/interviews/sessions/{id}/turn` more than once per 2 seconds
- WebSocket audio turns should be throttled naturally by recording time
- Keep `user_id` consistent across all requests
- Store `interview_id` and `interview_session_id` in frontend state for continuity
- On page reload, query `/api/interviews` to restore state

---

## 19) Testing endpoints locally

### Curl collector start
```bash
curl -X POST http://localhost:8000/api/collector/start \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user"}'
```

### Curl collector turn
```bash
curl -X POST http://localhost:8000/api/collector/1/turn \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user","user_message":"Backend"}'
```

### Curl interview start
```bash
curl -X POST http://localhost:8000/api/interviews/1/start \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user"}'
```

### WebSocket test (using wscat)
```bash
npm install -g wscat
wscat -c 'ws://localhost:8000/api/interviews/sessions/1/voice?user_id=test_user'
# Then type messages as JSON
{"type":"user_text","text":"My answer"}
```

