# ============================================================
#  welcome.py — MILESTONE 2: Feature 1
#  Welcome Prompt Service
#  Triggered when someone calls your Twilio number
# ============================================================

from fastapi import APIRouter, Form
from fastapi.responses import Response
from datetime import datetime
import database as db

router = APIRouter()

def xml(content: str):
    return Response(content=content, media_type="application/xml")


# ── WELCOME ENDPOINT ─────────────────────────────────────────
# Twilio calls this when a call comes in
@router.post("/ivr/welcome")
async def welcome(From: str = Form(...), CallSid: str = Form(...)):

    # Save session
    db.sessions[CallSid] = {
        "caller": From,
        "started": datetime.now().strftime("%H:%M:%S")
    }

    # Log incoming call
    db.log_call(caller=From, action="incoming_call", status="connected")

    twiml = """<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Gather numDigits="1" action="/ivr/menu" method="POST">
            <Say voice="Polly.Aditi" language="en-IN">
                Welcome to City Hospital Management System.
                Your health is our priority.
                Press 1 for New Patient Admission.
                Press 2 to Check Bed Availability.
                Press 3 for Emergency Services.
                Press 9 to Speak to Reception.
                Press star to repeat this menu.
            </Say>
        </Gather>
        <Say voice="Polly.Aditi" language="en-IN">
            We did not receive any input.
            Please call again. Thank you. Goodbye.
        </Say>
    </Response>"""

    return xml(twiml)
