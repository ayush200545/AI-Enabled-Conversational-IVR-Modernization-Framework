# AI-Enabled Conversational IVR Modernization Framework

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Twilio](https://img.shields.io/badge/Twilio-Programmable%20Voice-F22F46?style=flat&logo=twilio&logoColor=white)](https://twilio.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-412991?style=flat&logo=openai&logoColor=white)](https://openai.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Built for the **Infosys BFS Internship program** as part of a group project on AI-enabled hospital management. My subtopic is **Patient Admission & Bed Availability** — the part of the IVR that handles calls from families trying to admit a patient, check whether a ward has space, or find out what's happening with a patient already admitted.

There are three milestones. The first two were design and a basic DTMF backend. Milestone 3 — the bulk of this repo — is where the interesting stuff is: speech input, GPT-powered intent detection, and a session layer that keeps context alive when a call spans multiple turns.

---

## What this actually does

When someone calls the hospital number, they used to hear "press 1 for beds, press 2 for admission" and navigate a tree of menus. That works fine until someone is flustered, elderly, or calling in an emergency — at which point it falls apart immediately.

This version lets callers just say what they want:

> *"Is there a bed available in the ICU?"*
> *"I need to admit my father urgently"*
> *"What's the condition of patient P1001?"*
> *"Tell me about the maternity ward"*

The system figures out the intent, extracts whatever it needs (ward name, patient ID, urgency level), and asks follow-up questions if something's missing. A 4-step admission request works entirely through natural speech, and earlier answers stay in memory so the caller doesn't have to repeat themselves partway through.

---

## Tech stack

| What | How |
|------|-----|
| Web framework | FastAPI |
| IVR platform | Twilio Programmable Voice (TwiML) |
| Speech-to-text | Built into Twilio via Google Speech API — no separate service |
| Intent detection | OpenAI GPT-3.5-turbo, falls back to keyword matching if unavailable |
| Text-to-speech | Amazon Polly, Aditi voice (Indian English) |
| Session state | In-memory dict keyed by `CallSid`, Redis-compatible interface |
| Webhook security | HMAC-SHA1 signature validation on every `/ivr/*` request |

---

## Project structure

```
AI-Enabled-Conversational-IVR-Modernization-Framework/
│
├── main.py                        # App entry point, middleware wiring
├── requirements.txt
├── .env.example
├── README.md
│
└── milestone3/
    ├── middleware/
    │   └── twilio_security.py     # Validates every Twilio webhook signature
    │
    ├── routers/
    │   ├── ivr_router.py          # All 15+ call flow endpoints
    │   └── admin_router.py        # Monitoring and debug endpoints
    │
    ├── services/
    │   ├── nlu_service.py         # GPT intent + entity detection
    │   └── session_manager.py     # Per-call state across turns
    │
    ├── data/
    │   └── hospital_db.py         # Mock data: 8 wards, 4 patients
    │
    └── utils/
        └── twiml_builder.py       # TwiML + SSML response generation
```

---

## Milestones

### Milestone 1 — System design
Architecture diagrams, technology selection, flow documentation. No code.

### Milestone 2 — DTMF IVR backend
A working FastAPI server where callers press numbers to navigate menus. Functional but rigid — every input is a digit, every path is predetermined.

### Milestone 3 — Conversational AI layer *(this repo)*

Everything in Milestone 2 still works. On top of that:

Speech input via `<Gather input="speech">` — Twilio handles transcription natively, so there's no separate STT service to manage. GPT-3.5 takes the transcript and returns structured intent JSON. If GPT is unavailable for any reason, keyword matching picks up automatically with no error to the caller.

The admission flow is the most complex part. It collects patient name, ward choice, urgency level, and confirmation across four separate webhook calls — all tied together by `CallSid`. The session layer is what makes that possible.

Other additions: SSML on all responses (pauses, spell-out for patient IDs and bed numbers), 3-strike escalation to a human agent after consecutive failed recognitions, Twilio HMAC-SHA1 webhook validation so random traffic can't trigger the IVR, and a set of admin endpoints for monitoring active calls and ward data during a demo.

---

## The four call flows

### Bed availability

The caller names a ward (or asks for all wards) and gets the current bed count, occupancy rate, floor, and direct extension. If the ward is full, the system offers to check an alternative or transfer to admissions.

```
"Are there beds in ICU?"
→ ICU: 2 of 10 beds available. 80% occupied.
  Located on the First Floor. Extension 200.
```

### Patient admission — 4-step multi-turn

This one collects four things across four turns. Each answer is saved to the session so later turns can read earlier ones.

```
Turn 1: "I want to admit my mother"
Turn 2: [patient name] → "Priya Mehta"
Turn 3: [which ward?] → "General ward"
Turn 4: [urgency?] → "Routine"
Turn 5: [confirm?] → "Yes"
→ Request submitted. Reference: REQ48291.
  The General Ward team will contact you within 30 minutes.
```

### Patient status

The caller gives a patient ID or name, the system looks them up and reads back their ward, bed number, attending doctor, admission date, and current status.

```
"Status of P1004"
→ Sunita Mehta. Status: Critical.
  Neurology Ward, bed NEU-02. Dr. Arjun Nair.
  Admitted 10 March 2024.
```

### Ward inquiry

Basic information about any of the eight wards — what it specialises in, which floor, how many beds, current availability, and which extension to call directly.

---

## Hospital data

Eight wards are in the mock database:

| Ward | Specialty | Total beds | Available |
|------|-----------|-----------|-----------|
| General | General Medicine | 40 | 12 |
| ICU | Critical Care | 10 | 2 |
| Emergency | Emergency Medicine | 20 | 5 |
| Pediatric | Pediatrics | 15 | 7 |
| Maternity | Obs & Gynae | 18 | 4 |
| Cardiology | Cardiology | 12 | 3 |
| Orthopedic | Orthopedics | 14 | 6 |
| Neurology | Neurology | 10 | 1 |

Four sample patients are pre-loaded for status query demos: P1001 through P1004, each in a different ward.

---

## How NLU works

When Twilio sends a transcribed `SpeechResult`, the NLU service sends it to GPT-3.5 with a strict system prompt that returns JSON only:

```json
{
  "intent": "bed_availability",
  "confidence": 0.93,
  "entities": {
    "ward_name": "icu",
    "patient_id": null,
    "patient_name": null,
    "urgency": null
  },
  "interpreted_as": "Caller wants to check bed availability in the ICU"
}
```

If GPT is unavailable — network issue, API down, no key — it falls back to keyword matching that covers the same intents without any API call. The IVR keeps working either way, just with simpler matching.

When confidence comes back below 0.65, the system reads its interpretation back to the caller and asks them to confirm before doing anything with it.

---

## Webhook security

Every POST to `/ivr/*` goes through `TwilioSignatureMiddleware` before hitting any route handler.

Twilio signs each outbound webhook with `HMAC-SHA1(auth_token, full_url + sorted_POST_params)` and puts the result in `X-Twilio-Signature`. The middleware recomputes the same hash and compares using `hmac.compare_digest` — constant-time, so it's not vulnerable to timing attacks.

Three modes, set by environment variable:

- `enforce` — rejects anything without a valid signature with HTTP 403
- `log_only` — logs a warning but lets the request through (useful for debugging)
- `disabled` — skips validation entirely (happens automatically if `TWILIO_AUTH_TOKEN` isn't set)

For local development, leaving the auth token blank is enough — validation disables itself.

---

## Running it locally

**Prerequisites:** Python 3.11+, a Twilio account with a phone number, ngrok (free tier is fine)

```bash
# 1. Clone and install
git clone https://github.com/ayush200545/AI-Enabled-Conversational-IVR-Modernization-Framework.git
cd AI-Enabled-Conversational-IVR-Modernization-Framework
pip install -r requirements.txt

# 2. Create .env
cp .env.example .env
# Fill in OPENAI_API_KEY and TWILIO_AUTH_TOKEN

# 3. Start the server
uvicorn main:app --reload --port 8000

# 4. Expose it (second terminal)
ngrok http 8000
```

Then go to Twilio Console → Phone Numbers → your number → Voice Configuration, and set the webhook to:

```
https://<your-ngrok-url>/ivr/welcome
```

Call the number. You should hear the Aditi voice welcome.

**No OpenAI key?** The IVR still works. It drops to keyword-based intent detection automatically. Good enough for testing most flows.

---

## Environment variables

```bash
# Required for GPT NLU (optional — falls back to keywords without it)
OPENAI_API_KEY=sk-...

# Twilio credentials (from console.twilio.com → Account Info)
TWILIO_ACCOUNT_SID=ACxxxxxxxx...
TWILIO_AUTH_TOKEN=your_auth_token

# Webhook validation mode: enforce | log_only | disabled
# Defaults to disabled if TWILIO_AUTH_TOKEN is not set
TWILIO_VALIDATION_MODE=log_only

# Number to transfer calls to when the 3-strike limit hits
HOSPITAL_AGENT_NUMBER=+919800000000
```

---

## Testing without a phone

All endpoints accept plain form POST requests, so you can test the full conversation flow with curl:

```bash
# Trigger the welcome message
curl -X POST http://localhost:8000/ivr/welcome \
  -d "CallSid=TEST001"

# Simulate speech: "I want to check ICU beds"
curl -X POST http://localhost:8000/ivr/intent \
  -d "CallSid=TEST001&SpeechResult=I+want+to+check+ICU+beds&Confidence=0.92"

# Press 1 (DTMF, no speech required)
curl -X POST http://localhost:8000/ivr/intent \
  -d "CallSid=TEST001&Digits=1"

# Patient status by ID
curl -X POST http://localhost:8000/ivr/patient-status-response \
  -d "CallSid=TEST001&SpeechResult=P1001&Confidence=0.95"

# Start admission, give patient name
curl -X POST http://localhost:8000/ivr/admission/name \
  -d "CallSid=TEST001&SpeechResult=Rahul+Sharma&Confidence=0.88"
```

The full Swagger UI is at `http://localhost:8000/docs` with every endpoint listed and testable.

---

## Admin endpoints

These are not exposed in production but are useful during development and demos:

| Endpoint | What it shows |
|----------|---------------|
| `GET /admin/status` | Hospital-wide stats, active call count, pending admissions |
| `GET /admin/beds` | Bed availability across all eight wards |
| `GET /admin/patients` | All pre-loaded patient records |
| `GET /admin/admission-requests` | Admission requests submitted during this session |
| `GET /admin/sessions` | Active call sessions and their current stage |
| `GET /security` | Current webhook validation mode and config |
| `GET /health` | Simple health check |

---

## Cost per call

Conversational calls cost more than DTMF. For a typical 3-minute, 5-turn call:

| Component | Cost |
|-----------|------|
| Voice (3 min) | ₹3.24 |
| Twilio speech recognition (5 requests) | ₹8.30 |
| Twilio TTS (5 responses) | ₹1.65 |
| OpenAI GPT-3.5 (5 requests) | ₹0.85 |
| **Total** | **~₹14** |

A DTMF-only call costs about ₹3. The gap is real. Whether it's worth it depends on who's calling. For a hospital where the caller might be elderly, distressed, or unfamiliar with menu navigation, ₹11 extra per call is probably fine. For a billing hotline where callers are comfortable pressing numbers, it probably isn't. This IVR uses `<Gather input="dtmf speech">` on every prompt, so both modes work simultaneously — callers who prefer buttons can still use them.

---

## What could be better

**Redis sessions.** The current in-memory dict loses all state on server restart. The session manager interface is already compatible with Redis — it's a one-line swap, just not done yet because it adds a dependency that needs a running Redis instance.

**A real database.** Ward and patient data lives in a Python dict in `hospital_db.py`. It's mock data, and it shows. A PostgreSQL backend would drop in without touching the NLU or session code at all.

**Hindi support.** Twilio supports `language="hi-IN"` in `<Gather>`, and Polly has Hindi audio too. The intent detection prompt would need expanding, but the architecture doesn't need to change. This probably matters more than most of the other items on this list — a lot of hospital callers in India aren't comfortable in English.

**SMS confirmation.** After a successful admission request, sending the reference number as an SMS would be straightforward with Twilio's messaging API. The credentials are already in the config.

**An actual test suite.** `twilio_security.py` exports `compute_test_signature()` specifically so tests can generate valid signed requests. Nobody's written the tests yet.

---

## Group project context

This is one subtopic within a larger group project on hospital IVR modernization. Other subtopics in the group cover appointment scheduling, prescription refills, and lab result queries. The shared architecture — FastAPI, Twilio, GPT-3.5 — is consistent across subtopics so the pieces could theoretically be combined into one system.

---

## License

MIT. Use it however you want.
