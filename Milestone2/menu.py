# ============================================================
#  menu.py — MILESTONE 2: Feature 2 + Feature 3
#  Menu Driven  → plays options (Press 1, 2, 3, 9)
#  Menu Handle  → processes digit and routes to correct flow
# ============================================================

from fastapi import APIRouter, Form
from fastapi.responses import Response
import database as db

router = APIRouter()

def xml(content: str):
    return Response(content=content, media_type="application/xml")


# ── MAIN MENU HANDLER ────────────────────────────────────────
# Receives digit pressed by caller and routes accordingly
@router.post("/ivr/menu")
async def handle_menu(
    Digits: str = Form(...),
    CallSid: str = Form(...),
    From: str = Form(...)
):
    # Update session
    if CallSid in db.sessions:
        db.sessions[CallSid]["last_press"] = Digits

    # ── ROUTE BASED ON DIGIT PRESSED ────────────────────────
    if Digits == "1":
        db.log_call(caller=From, action="selected_admission", status="navigating")
        return admission_menu()

    elif Digits == "2":
        db.log_call(caller=From, action="selected_bed_check", status="navigating")
        return bed_menu()

    elif Digits == "3":
        db.log_call(caller=From, action="emergency", status="alerted")
        return emergency_menu()

    elif Digits == "9":
        db.log_call(caller=From, action="transfer_reception", status="transferred")
        return transfer_to_agent()

    elif Digits == "*":
        # Repeat main menu
        return repeat_menu()

    else:
        db.log_call(caller=From, action="invalid_input", status="error")
        return invalid_option()


# ── SUB MENU: Admission ───────────────────────────────────────
def admission_menu():
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Gather numDigits="1" action="/ivr/admission" method="POST">
            <Say voice="Polly.Aditi" language="en-IN">
                You selected Patient Admission.
                Please select the ward.
                Press 1 for General Ward.
                Press 2 for I C U.
                Press 3 for Maternity Ward.
                Press 0 to return to main menu.
            </Say>
        </Gather>
    </Response>"""
    return xml(twiml)


# ── SUB MENU: Bed Availability ────────────────────────────────
def bed_menu():
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Gather numDigits="1" action="/ivr/bed-status" method="POST">
            <Say voice="Polly.Aditi" language="en-IN">
                You selected Bed Availability.
                Press 1 for General Ward.
                Press 2 for I C U.
                Press 3 for Maternity Ward.
                Press 0 to return to main menu.
            </Say>
        </Gather>
    </Response>"""
    return xml(twiml)


# ── EMERGENCY ─────────────────────────────────────────────────
def emergency_menu():
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say voice="Polly.Aditi" language="en-IN">
            You have selected Emergency Services.
            Please proceed to our emergency entrance immediately.
            Our emergency response team has been notified.
            For life threatening situations, please call 1 0 8 immediately.
            Thank you. Stay safe.
        </Say>
        <Hangup/>
    </Response>"""
    return xml(twiml)


# ── TRANSFER TO RECEPTION ─────────────────────────────────────
def transfer_to_agent():
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say voice="Polly.Aditi" language="en-IN">
            Please hold. We are transferring you to our reception desk.
            Thank you for your patience.
        </Say>
        <Hangup/>
    </Response>"""
    return xml(twiml)


# ── REPEAT MENU ───────────────────────────────────────────────
def repeat_menu():
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Gather numDigits="1" action="/ivr/menu" method="POST">
            <Say voice="Polly.Aditi" language="en-IN">
                Press 1 for New Patient Admission.
                Press 2 to Check Bed Availability.
                Press 3 for Emergency Services.
                Press 9 to Speak to Reception.
                Press star to repeat this menu.
            </Say>
        </Gather>
    </Response>"""
    return xml(twiml)


# ── INVALID INPUT ─────────────────────────────────────────────
def invalid_option():
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Gather numDigits="1" action="/ivr/menu" method="POST">
            <Say voice="Polly.Aditi" language="en-IN">
                That was an invalid option.
                Press 1 for Admission.
                Press 2 for Bed Availability.
                Press 3 for Emergency.
                Press 9 for Reception.
            </Say>
        </Gather>
    </Response>"""
    return xml(twiml)
