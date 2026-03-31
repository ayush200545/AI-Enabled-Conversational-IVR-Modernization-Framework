# AI-Enabled Conversational IVR Modernization Framework

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Twilio](https://img.shields.io/badge/Twilio-Programmable%20Voice-F22F46?style=flat&logo=twilio&logoColor=white)](https://twilio.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-412991?style=flat&logo=openai&logoColor=white)](https://openai.com)
[![pytest](https://img.shields.io/badge/pytest-8.0-0A9EDC?style=flat&logo=pytest&logoColor=white)](https://pytest.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg)](LICENSE)
[![Deployed on Render](https://img.shields.io/badge/Deployed-Render-46E3B7?style=flat&logo=render&logoColor=white)](https://hospital-ivr.onrender.com)

> **Infosys BFS Internship — Group Project**
> **Domain:** Hospital Management System
> **My Subtopic:** Patient Admission & Bed Availability Management IVR
> **Duration:** 02 February 2026 — 02 April 2026

---

## 🚀 Live Deployment

| Service | URL |
|---------|-----|
| **Production API** | https://hospital-ivr.onrender.com |
| **Health Check** | https://hospital-ivr.onrender.com/health |
| **API Documentation** | https://hospital-ivr.onrender.com/docs |
| **Admin Dashboard** | https://hospital-ivr.onrender.com/admin/status |
| **Security Status** | https://hospital-ivr.onrender.com/security |

> Configure your Twilio phone number webhook to: `https://hospital-ivr.onrender.com/ivr/welcome`

---

## 📋 Table of Contents

- [What This Does](#-what-this-does)
- [Project Timeline](#-project-timeline)
- [Tech Stack](#-tech-stack)
- [Repository Structure](#-repository-structure)
- [Milestones](#-milestones)
- [The Four IVR Flows](#-the-four-ivr-flows)
- [Hospital Data](#-hospital-data)
- [Running Locally](#-running-locally)
- [Running Tests](#-running-tests)
- [API Reference](#-api-reference)
- [Artifacts](#-artifacts)
- [Environment Variables](#-environment-variables)
- [License](#-license)

---

## 💡 What This Does

Old hospital IVR: *"Press 1 for beds, press 2 for admission, press 3 for..."*

This project: callers just say what they need.

> *"Are there any beds available in the ICU?"*
> *"I need to admit my father urgently."*
> *"What is the condition of patient P1001?"*
> *"Tell me about the maternity ward."*

The system figures out intent using GPT-3.5, extracts entities (ward name, patient ID, urgency), keeps track of earlier answers across a multi-turn call so callers don't repeat themselves, and responds in Amazon Polly's Aditi voice — Indian English with natural pauses and proper pronunciation.

The gap this solves: button-press menus fail the moment a caller is elderly, distressed, or calling during an emergency. Pressing "3 then 2 then 1" when someone is trying to admit a critically ill patient is a bad experience. Saying "I need to admit my mother urgently" is not.

---

## 📅 Project Timeline

| Event | Date |
|-------|------|
| Project Start | 02 February 2026 |
| Milestone 1 — System Design | 16 February 2026 |
| Milestone 2 — DTMF IVR Backend | 02 March 2026 |
| Milestone 3 — Conversational AI Layer | 16 March 2026 |
| Milestone 4 — Testing & Deployment | 29 March 2026 |
| Internal Demo | 26 March 2026 |
| Team Demo | 27 March 2026 |
| Final Submission | 29 March 2026 |

---

## 🛠 Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Web Framework | FastAPI 0.115 | Async, fast, auto-docs |
| IVR Platform | Twilio Programmable Voice | Native STT built into `<Gather>` — no separate Speech Service |
| Speech-to-Text | Twilio native (Google Speech API) | en-IN model for Indian English |
| Intent Detection | OpenAI GPT-3.5-turbo | Extracts intent + entities (ward, patient ID, urgency) from free speech |
| NLU Fallback | Keyword matching | Auto-activates if GPT is unavailable — IVR never fails silently |
| Text-to-Speech | Amazon Polly — Aditi voice | Indian English, natural pacing via SSML |
| Session State | In-memory dict (CallSid-keyed) | Redis-compatible interface — one-line swap for production scaling |
| Webhook Security | HMAC-SHA1 signature validation | Every `/ivr/*` request verified against `X-Twilio-Signature` |
| Testing | pytest 8 + FastAPI TestClient | GPT mocked via `unittest.mock.patch` — tests run <50ms each |
| Deployment | Render (HTTPS) | Free tier with health check keep-alive |

---

## 📁 Repository Structure

```
AI-Enabled-Conversational-IVR-Modernization-Framework/
│
├── main.py                          # FastAPI entry point, middleware wiring
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variable template
├── LICENSE                          # MIT License
├── README.md
│
├── milestone3/                      # All IVR code (M2 + M3 + M4)
│   ├── middleware/
│   │   └── twilio_security.py       # HMAC-SHA1 webhook validator (3 modes)
│   ├── routers/
│   │   ├── ivr_router.py            # 15+ Twilio webhook endpoints
│   │   └── admin_router.py          # Monitoring: /admin/status, /beds, etc.
│   ├── services/
│   │   ├── nlu_service.py           # GPT-3.5 intent + entity detection + fallback
│   │   └── session_manager.py       # Per-call state across turns (CallSid-keyed)
│   ├── data/
│   │   └── hospital_db.py           # Mock data: 8 wards, 4 patients
│   └── utils/
│       └── twiml_builder.py         # TwiML + SSML response generator
│
├── milestone4/                      # Full test suite (M4)
│   └── tests/
│       ├── conftest.py              # Session cleanup, env config, test fixtures
│       ├── test_unit.py             # 67 unit tests, 12 test classes
│       ├── test_integration.py      # Integration tests: session + DB + flows
│       └── test_e2e.py              # 4 E2E journeys + performance tests
│
└── artifacts/                       # Infosys submission artifacts
    ├── Full_Agile_Template.xlsx     # Product backlog, sprint tasks, standup, retro
    ├── Full_Unit_Test_Plan.xlsx     # 67 test cases across M1–M4
    └── Full_Defect_Tracker.xlsx     # 30 defects logged and closed across all sprints
```

---

## 📍 Milestones

### Milestone 1 — System Design *(submitted 16 Feb 2026)*

Designed the complete five-layer IVR architecture before writing any code. Defined all API contracts upfront — every `/ivr/*` endpoint had its method, parameters, and response format documented before M2 development started. Chose Twilio over Azure specifically because speech recognition is built into `<Gather>`, eliminating a separate STT service. Technology comparison: Twilio vs Azure vs Web Simulator.

**Deliverables:** Architecture diagrams · Technology selection with justification · API contracts for 15 endpoints · Hospital data model · Sprint plan

---

### Milestone 2 — DTMF IVR Backend *(submitted 02 Mar 2026)*

Working FastAPI server where callers press numbers to navigate menus. Five complete flows: bed availability, patient admission, patient status, ward inquiry, and agent transfer. Hospital mock database with 8 wards and 4 pre-loaded patients. Live on Twilio via ngrok, all five flows verified with real calls.

**Deliverables:** `main.py` · `ivr_router.py` (DTMF version) · `hospital_db.py` · `admin_router.py` · Twilio webhook configured

---

### Milestone 3 — Conversational AI Layer *(submitted 16 Mar 2026)*

Everything in M2, plus natural speech, GPT NLU, Polly TTS, multi-turn sessions, and webhook security.

The admission flow is the most complex part: four sequential webhook calls, all with the same `CallSid`, collecting patient name → ward → urgency → confirmation. The session layer keeps each answer in memory so the caller doesn't repeat themselves. The confirmation step reads everything back with `prosody rate=slow` so the caller can verify clearly.

Other additions: SSML throughout (pauses, spell-out for patient IDs, emphasis for critical info), 3-strike escalation to human agent, low-confidence gating (below 0.65 triggers a confirmation prompt before acting), and Twilio HMAC-SHA1 webhook validation in three modes: `enforce` for production, `log_only` for staging, `disabled` auto-activates when no auth token is set.

**Deliverables:** `nlu_service.py` · `session_manager.py` · `twiml_builder.py` · `twilio_security.py` · Updated `ivr_router.py` · Deployed to Render

---

### Milestone 4 — Testing & Deployment *(submitted 29 Mar 2026)*

Full test coverage across four layers. GPT is patched with `unittest.mock.patch` on every speech test — tests never make real API calls and each runs in under 50ms.

**Unit tests (`test_unit.py`):** 67 test cases across 12 classes covering every endpoint, all 8 wards (via `@pytest.mark.parametrize`), DTMF routing, NLU routing, session manager CRUD, error handling paths, and admin endpoints. `conftest.py` clears session state before every test.

**Integration tests (`test_integration.py`):** Real session state, real DB lookups, only NLU mocked. Key test: patient name from step 2 must appear in the step 5 confirmation — proves session persists across turns. All 4 patients tested parametrically. Denial at confirmation restarts the flow.

**E2E tests (`test_e2e.py`):** Four complete user journeys — full admission happy path (7 webhook calls ending in REQ reference), DTMF bed check, 3-strike escalation, and multi-flow call. Performance tests enforce `<2s` per webhook (Twilio's limit is 15s), 20-request load test, and 3-thread concurrency test for session isolation.

**Production:** Deployed on Render with `TWILIO_VALIDATION_MODE=enforce`. Health check every 5 minutes keeps the instance warm.

**Deliverables:** `test_unit.py` · `test_integration.py` · `test_e2e.py` · `conftest.py` · `pytest.ini` · 3 Excel artifacts

---

## 🔄 The Four IVR Flows

### 1. Bed Availability

```
Caller: "Are there beds in the ICU?"
   ↓  GPT: intent=bed_availability, ward=icu
System: "ICU has 2 of 10 beds available. Occupancy 80%.
         First Floor. Extension 2-0-0."
```

If the ward is full, the system offers to check an alternative or transfer to admissions directly.

### 2. Patient Admission — 4-step multi-turn

```
Turn 1  "I want to admit my father"     → asks for patient name
Turn 2  "Rajesh Kumar"                  → asks which ward
Turn 3  "Cardiology"                    → asks urgency level
Turn 4  "Routine"                       → reads back all three, asks to confirm
Turn 5  "Yes, correct"                  → REQ48291 generated
         "Cardiology team will contact you within 30 minutes."
```

### 3. Patient Status

```
Caller: "What is the condition of patient P 1 0 0 4?"
System: "Sunita Mehta. Status: Critical.
         Neurology Ward, bed N-E-U-zero-two.
         Attending doctor: Dr. Arjun Nair."
```

### 4. Ward Inquiry

```
Caller: "Tell me about the maternity ward."
System: "Maternity Ward specialises in Obstetrics and Gynaecology.
         Third Floor. 4 of 18 beds currently available.
         Extension: 4-1-0."
```

---

## 🏥 Hospital Data

Eight wards in the mock database:

| Ward | Specialty | Total Beds | Available |
|------|-----------|-----------|-----------|
| General | General Medicine | 40 | 12 |
| ICU | Critical Care | 10 | 2 |
| Emergency | Emergency Medicine | 20 | 5 |
| Pediatric | Pediatrics | 15 | 7 |
| Maternity | Obs & Gynae | 18 | 4 |
| Cardiology | Cardiology | 12 | 3 |
| Orthopedic | Orthopedics | 14 | 6 |
| Neurology | Neurology | 10 | 1 |

Four pre-loaded patients for status query demos:

| ID | Name | Ward | Status |
|----|------|------|--------|
| P1001 | Rahul Sharma | Cardiology | Admitted |
| P1002 | Priya Patel | Maternity | Admitted |
| P1003 | Amit Singh | Pediatric | Under Observation |
| P1004 | Sunita Mehta | Neurology | **Critical** |

---

## 💻 Running Locally

**Prerequisites:** Python 3.11+, a Twilio account with a phone number, ngrok

```bash
# 1. Clone and install
git clone https://github.com/ayush200545/AI-Enabled-Conversational-IVR-Modernization-Framework.git
cd AI-Enabled-Conversational-IVR-Modernization-Framework
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env — add OPENAI_API_KEY and TWILIO_AUTH_TOKEN

# 3. Run
uvicorn main:app --reload --port 8000

# 4. Expose (second terminal)
ngrok http 8000
# Copy the https URL
```

In Twilio Console → Phone Numbers → your number → Voice Configuration:
- **A call comes in:** Webhook · HTTP POST · `https://<ngrok-url>/ivr/welcome`
- **Call Status Changes:** `https://<ngrok-url>/ivr/call-status`

Call the number and say *"check ICU beds"*.

**No OpenAI key?** Keyword fallback kicks in automatically. All flows still work, just with simpler intent matching.

---

## 🧪 Running Tests

```bash
# Set test environment (conftest.py does this automatically)
export TWILIO_VALIDATION_MODE=disabled
export OPENAI_API_KEY=sk-test-anything

# All tests
pytest milestone4/tests/ -v

# By layer
pytest milestone4/tests/test_unit.py -v
pytest milestone4/tests/test_integration.py -v
pytest milestone4/tests/test_e2e.py -v -k "not performance"

# Performance tests only
pytest milestone4/tests/test_e2e.py -v -k "performance"

# Filter by keyword
pytest milestone4/tests/ -v -k "admission"

# With coverage report
pytest milestone4/tests/ --cov=milestone3 --cov-report=term-missing
```

All 67 tests pass. No test makes a real OpenAI or Twilio API call.

---

## 📡 API Reference

### Twilio Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/POST` | `/ivr/welcome` | **Entry point** — set as Twilio webhook |
| `POST` | `/ivr/menu` | Main menu (hybrid DTMF + speech) |
| `POST` | `/ivr/intent` | Central intent router (GPT NLU) |
| `POST` | `/ivr/bed-availability-response` | Ward selection handler |
| `POST` | `/ivr/admission/name` | Admission step 1: patient name |
| `POST` | `/ivr/admission/ward` | Admission step 2: ward selection |
| `POST` | `/ivr/admission/urgency` | Admission step 3: urgency level |
| `POST` | `/ivr/admission/confirm` | Admission step 4: confirmation |
| `POST` | `/ivr/patient-status-response` | Patient lookup by ID or name |
| `POST` | `/ivr/ward-info-response` | Ward information |
| `POST` | `/ivr/post-action` | Continue or end call |
| `POST` | `/ivr/call-status` | Twilio call lifecycle callback |

### Admin & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/admin/status` | Hospital stats + active call count |
| `GET` | `/admin/wards` | All 8 ward records |
| `GET` | `/admin/beds` | Bed availability overview |
| `GET` | `/admin/patients` | Patient records |
| `GET` | `/admin/admission-requests` | Submitted admission requests |
| `GET` | `/admin/sessions` | Active call sessions |
| `GET` | `/security` | Webhook validation config |
| `GET` | `/health` | Health probe |
| `GET` | `/docs` | Swagger UI (interactive) |

---

## 📂 Artifacts

All three required Infosys submission artifacts are in the `/artifacts` folder:

| File | Contents |
|------|----------|
| `Full_Agile_Template.xlsx` | Product Backlog (24 user stories) · Sprint Backlog (44 tasks) · Daily Stand-up Log (29 entries Feb–Apr) · Sprint Retrospection (4 sprints) · Milestone Timeline |
| `Full_Unit_Test_Plan.xlsx` | 67 test cases across M1–M4 · Per-milestone sheets · Summary with pass rate formulas |
| `Full_Defect_Tracker.xlsx` | 30 defects logged and closed across all 4 sprints · Summary by sprint and defect type |

---

## ⚙️ Environment Variables

```bash
# Required for GPT NLU (falls back to keywords if not set)
OPENAI_API_KEY=sk-...

# Twilio credentials — from console.twilio.com → Account Info
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here

# Webhook validation: enforce | log_only | disabled
# Auto-disabled when TWILIO_AUTH_TOKEN is not set
TWILIO_VALIDATION_MODE=enforce

# Transfer destination when 3-strike limit hits
HOSPITAL_AGENT_NUMBER=+919800000000
```

---

## 🔒 Security

Every POST to `/ivr/*` passes through `TwilioSignatureMiddleware` before reaching any route handler.

Twilio signs each outbound webhook: `HMAC-SHA1(auth_token, full_url + sorted_POST_params)` → `X-Twilio-Signature` header. The middleware recomputes the same hash using `hmac.compare_digest` (timing-safe) and rejects anything that doesn't match.

Three modes via `TWILIO_VALIDATION_MODE`:
- `enforce` — HTTP 403 on invalid signature (production)
- `log_only` — logs a warning but passes through (staging)
- `disabled` — auto-enabled when no auth token is set (local dev)

---

## 🌱 What Could Be Better

**Redis sessions.** The in-memory session dict loses state on restart. The `session_manager.py` interface is already Redis-compatible — it's a one-line swap in production.

**Real database.** Ward and patient data live in a Python dict. PostgreSQL with SQLAlchemy would drop in without changing any NLU or session code.

**Hindi support.** Twilio supports `language="hi-IN"` in `<Gather>`, and Polly has Hindi audio too. This matters more than anything else on this list for a hospital serving Indian patients who aren't comfortable in English.

**SMS confirmation.** After a successful admission request, sending the REQ reference by SMS is a few lines with Twilio's Messaging API — credentials are already in the config.

---

## 👥 Group Project Context

This is one subtopic in a larger group project on hospital IVR modernization for the Infosys BFS Internship. Other subtopics in the group cover appointment scheduling, prescription refills, and lab result queries. Shared stack across all subtopics: FastAPI + Twilio + GPT-3.5.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for full terms.
