"""
City General Hospital IVR System
Main FastAPI Application

Milestone 2: Basic IVR backend with /ivr endpoints
Milestone 3: Twilio Conversational AI Layer (Speech + GPT NLU + Multi-turn sessions)
             + Twilio Webhook Signature Validation (Security Middleware)

Run:
    uvicorn main:app --reload --port 8000

Expose via ngrok:
    ngrok http 8000
    Then set Twilio webhook to: https://<ngrok-url>/ivr/welcome

Environment Variables (see .env.example):
    OPENAI_API_KEY            — Required for GPT NLU
    TWILIO_AUTH_TOKEN         — Required for webhook signature validation
    TWILIO_VALIDATION_MODE    — "enforce" | "log_only" | "disabled" (default: enforce)
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from milestone3.routers.ivr_router import router as ivr_router
from milestone3.routers.admin_router import router as admin_router
from milestone3.middleware.twilio_security import (
    TwilioSignatureMiddleware,
    get_security_status,
)

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("hospital_ivr")


# ─────────────────────────────────────────────
#  APP LIFECYCLE
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    sec = get_security_status()
    logger.info("🏥 City General Hospital IVR System starting up...")
    logger.info("📞 Milestone 3: Conversational AI Layer active")
    logger.info("🔊 TTS  : Amazon Polly (Aditi) via Twilio")
    logger.info("🧠 NLU  : OpenAI GPT-3.5 + keyword fallback")
    logger.info("📡 STT  : Twilio native (Google Speech API)")
    logger.info(f"🔒 SEC  : Validation mode = {sec['validation_mode'].upper()}")
    logger.info(f"🔒 SEC  : {sec['recommendation']}")
    yield
    logger.info("🏥 Hospital IVR shutting down.")


# ─────────────────────────────────────────────
#  APP INIT
# ─────────────────────────────────────────────

app = FastAPI(
    title="City General Hospital IVR",
    description=(
        "**AI-Enabled Conversational IVR — Milestone 3**\n\n"
        "**Subtopic:** Patient Admission & Bed Availability Management\n\n"
        "**Stack:** Twilio STT · OpenAI GPT-3.5 NLU · Amazon Polly TTS · FastAPI\n\n"
        "**Security:** Twilio HMAC-SHA1 webhook signature validation"
    ),
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware (order matters — security runs first) ────────
# NOTE: Starlette adds middleware in reverse order of add_middleware calls.
#       The LAST add_middleware call runs FIRST on incoming requests.
#       So add TwilioSignatureMiddleware AFTER CORSMiddleware so it executes first.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.add_middleware(TwilioSignatureMiddleware)   # ← Runs first on every request


# ─────────────────────────────────────────────
#  ROUTERS
# ─────────────────────────────────────────────

app.include_router(ivr_router)
app.include_router(admin_router)


# ─────────────────────────────────────────────
#  ROOT & UTILITY ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/", tags=["Root"])
def root():
    return {
        "service": "City General Hospital — Conversational IVR",
        "milestone": "3 — Twilio Conversational AI Layer",
        "subtopic": "Patient Admission & Bed Availability Management",
        "version": "3.0.0",
        "security": get_security_status(),
        "endpoints": {
            "Twilio Entry Point": "POST /ivr/welcome",
            "Main Menu":         "POST /ivr/menu",
            "Admin Dashboard":   "GET  /admin/status",
            "Security Status":   "GET  /security",
            "API Docs":          "GET  /docs",
        },
        "flows": [
            "Bed Availability (by ward or overall summary)",
            "Patient Admission (4-step multi-turn: name → ward → urgency → confirm)",
            "Patient Status (lookup by ID or name)",
            "Ward / Department Inquiry",
            "Transfer to Human Agent (with 3-strike escalation)",
        ],
    }


@app.get("/health", tags=["Root"])
def health():
    """Lightweight health probe — no auth required, used by load balancers."""
    return {"status": "healthy", "service": "hospital-ivr-m3"}


@app.get("/security", tags=["Root"])
def security_status():
    """
    Returns current Twilio webhook security configuration.
    Safe to expose — contains no secrets.
    """
    return get_security_status()
