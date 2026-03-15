"""
IVR Router - All Twilio Webhook Endpoints
Hospital Patient Admission & Bed Availability IVR
Milestone 3 - Conversational AI Layer
"""

import logging
from fastapi import APIRouter, Form, Request
from fastapi.responses import Response
from typing import Optional

from ..services.nlu_service import detect_intent
from ..services.session_manager import (
    get_session, update_session, set_collected,
    get_collected, increment_retry, reset_retry, end_session
)
from ..data.hospital_db import (
    get_bed_availability, get_all_wards, find_patient,
    find_patient_by_name, create_admission_request,
    get_wards_with_availability, get_total_hospital_stats,
    get_ward_info, WARDS
)
from ..utils.twiml_builder import (
    welcome_twiml, main_menu_twiml, bed_availability_twiml,
    all_beds_summary_twiml, admission_start_twiml, admission_get_ward_twiml,
    admission_get_urgency_twiml, admission_confirm_twiml, admission_success_twiml,
    patient_status_ask_twiml, patient_found_twiml, patient_not_found_twiml,
    ward_info_twiml, transfer_to_agent_twiml, error_reprompt_twiml,
    goodbye_twiml, no_beds_twiml
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ivr", tags=["IVR"])

AGENT_NUMBER = "+919800000000"   # Hospital staff number — change in production
MAX_RETRIES = 3


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

async def _get_form(request: Request) -> dict:
    """Extract all Twilio POST params."""
    form = await request.form()
    return dict(form)


def _log_turn(call_sid: str, speech: str | None, intent_result: dict | None = None):
    session = get_session(call_sid)
    logger.info(
        f"[{call_sid[:8]}] Turn {session['turns']} | "
        f"Stage: {session['stage']} | "
        f"Speech: '{speech}' | "
        f"Intent: {intent_result['intent'] if intent_result else 'N/A'}"
    )


# ─────────────────────────────────────────────
#  ENTRY POINTS
# ─────────────────────────────────────────────

@router.get("/welcome")
@router.post("/welcome")
async def ivr_welcome(request: Request):
    """
    Entry point — Twilio calls this when call connects.
    Configure this URL in your Twilio phone number settings.
    """
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    get_session(call_sid)  # Initialise session
    logger.info(f"New call: {call_sid}")
    return welcome_twiml()


@router.post("/menu")
async def ivr_menu(request: Request):
    """Main menu with hybrid DTMF + speech."""
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    update_session(call_sid, {"stage": "menu"})
    return main_menu_twiml()


# ─────────────────────────────────────────────
#  INTENT ROUTER
# ─────────────────────────────────────────────

@router.post("/intent")
async def ivr_intent(request: Request):
    """
    Central intent router.
    Receives speech/DTMF from welcome/menu gather and routes accordingly.
    """
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    speech = form.get("SpeechResult", "").strip()
    digits = form.get("Digits", "").strip()
    confidence = float(form.get("Confidence", "1.0") or "1.0")

    _log_turn(call_sid, speech or digits)

    # ── DTMF shortcuts ─────────────────────────────
    if digits:
        dtmf_map = {
            "1": "bed_availability",
            "2": "patient_admission",
            "3": "patient_status",
            "4": "ward_inquiry",
            "0": "transfer_to_agent",
        }
        intent_name = dtmf_map.get(digits)
        if intent_name:
            update_session(call_sid, {"intent": intent_name, "stage": intent_name})
            reset_retry(call_sid)
            return _route_intent(call_sid, intent_name, {})

    # ── Speech NLU ─────────────────────────────────
    if not speech:
        retry = increment_retry(call_sid)
        if retry >= MAX_RETRIES:
            return transfer_to_agent_twiml(AGENT_NUMBER)
        return error_reprompt_twiml(retry)

    result = detect_intent(speech, confidence)
    intent = result["intent"]
    entities = result["entities"]
    _log_turn(call_sid, speech, result)

    # Low-confidence: ask for confirmation
    if result["confidence"] < 0.65 and intent not in ("confirm", "deny", "goodbye"):
        update_session(call_sid, {"pending_intent": intent, "pending_entities": entities, "stage": "low_conf_confirm"})
        from ..utils.twiml_builder import gather_speech, say, gather_close, twiml_response, CONFIRM_HINTS
        interpreted = result.get("interpreted_as", speech)
        body = "\n".join([
            gather_speech("/ivr/low-conf-confirm", hints=CONFIRM_HINTS),
            say(
                f"Just to confirm, you'd like help with: "
                f"{interpreted}. "
                f"Is that correct? Say yes or no."
            ),
            gather_close(),
        ])
        return twiml_response(body)

    reset_retry(call_sid)
    update_session(call_sid, {"intent": intent, "stage": intent})
    # Pre-fill entities from NLU
    if entities.get("ward_name"):
        set_collected(call_sid, "ward_name", entities["ward_name"])
    if entities.get("patient_id"):
        set_collected(call_sid, "patient_id", entities["patient_id"])
    if entities.get("patient_name"):
        set_collected(call_sid, "patient_name", entities["patient_name"])

    return _route_intent(call_sid, intent, entities)


def _route_intent(call_sid: str, intent: str, entities: dict) -> Response:
    """Route to the correct IVR flow based on detected intent."""
    if intent == "bed_availability":
        ward_key = entities.get("ward_name") or get_collected(call_sid, "ward_name")
        if ward_key:
            ward_data = get_bed_availability(ward_key)
            if ward_data:
                w = ward_data[ward_key]
                if w["available_beds"] == 0:
                    return no_beds_twiml(w["name"])
                return bed_availability_twiml(w, ward_key)
        return bed_availability_twiml()  # Ask which ward

    elif intent == "patient_admission":
        return admission_start_twiml()

    elif intent == "patient_status":
        pid = entities.get("patient_id") or get_collected(call_sid, "patient_id")
        if pid:
            patient = find_patient(pid)
            if patient:
                return patient_found_twiml(patient)
            return patient_not_found_twiml()
        return patient_status_ask_twiml()

    elif intent == "ward_inquiry":
        ward_key = entities.get("ward_name") or get_collected(call_sid, "ward_name")
        if ward_key:
            ward = get_ward_info(ward_key)
            return ward_info_twiml(ward)
        return ward_info_twiml()

    elif intent == "transfer_to_agent":
        return transfer_to_agent_twiml(AGENT_NUMBER)

    elif intent in ("goodbye", "cancel"):
        end_session(call_sid)
        return goodbye_twiml()

    elif intent == "repeat_menu":
        return main_menu_twiml()

    else:
        retry = increment_retry(call_sid)
        if retry >= MAX_RETRIES:
            return transfer_to_agent_twiml(AGENT_NUMBER)
        return main_menu_twiml(reprompt=True)


# ─────────────────────────────────────────────
#  LOW-CONFIDENCE CONFIRMATION
# ─────────────────────────────────────────────

@router.post("/low-conf-confirm")
async def low_conf_confirm(request: Request):
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    speech = form.get("SpeechResult", "").strip()
    digits = form.get("Digits", "")

    session = get_session(call_sid)
    pending_intent = session.get("pending_intent", "unknown")
    pending_entities = session.get("pending_entities", {})

    is_yes = (
        digits == "1"
        or any(w in speech.lower() for w in ["yes", "correct", "right", "okay", "ok", "haan"])
    )
    if is_yes:
        reset_retry(call_sid)
        return _route_intent(call_sid, pending_intent, pending_entities)
    else:
        return main_menu_twiml(reprompt=True)


# ─────────────────────────────────────────────
#  BED AVAILABILITY FLOW
# ─────────────────────────────────────────────

@router.post("/bed-availability-response")
async def bed_availability_response(request: Request):
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    speech = form.get("SpeechResult", "").strip()
    digits = form.get("Digits", "").strip()

    if not speech and not digits:
        retry = increment_retry(call_sid)
        return error_reprompt_twiml(retry)

    result = detect_intent(speech or digits)
    entities = result.get("entities", {})
    intent = result.get("intent")

    # Handle post-result navigation
    if intent in ("cancel", "goodbye"):
        return goodbye_twiml()
    if intent == "transfer_to_agent":
        return transfer_to_agent_twiml(AGENT_NUMBER)
    if intent == "patient_admission":
        return admission_start_twiml()
    if "main menu" in speech.lower() or digits == "0":
        return main_menu_twiml()

    # "all wards" request
    if "all" in speech.lower() or "overall" in speech.lower():
        stats = get_total_hospital_stats()
        available = get_wards_with_availability()
        return all_beds_summary_twiml(stats, available)

    ward_key = entities.get("ward_name") or get_collected(call_sid, "ward_name")
    if not ward_key:
        result2 = detect_intent(speech)
        ward_key = result2["entities"].get("ward_name")

    if ward_key:
        set_collected(call_sid, "ward_name", ward_key)
        ward_data = get_bed_availability(ward_key)
        if ward_data:
            w = ward_data[ward_key]
            if w["available_beds"] == 0:
                return no_beds_twiml(w["name"])
            return bed_availability_twiml(w, ward_key)

    # Unrecognised ward — re-ask
    retry = increment_retry(call_sid)
    if retry >= MAX_RETRIES:
        return transfer_to_agent_twiml(AGENT_NUMBER)
    return bed_availability_twiml()


# ─────────────────────────────────────────────
#  ADMISSION FLOW — MULTI-TURN
# ─────────────────────────────────────────────

@router.post("/admission/name")
async def admission_name(request: Request):
    """Step 1: Collect patient name."""
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    speech = form.get("SpeechResult", "").strip()

    if not speech:
        retry = increment_retry(call_sid)
        if retry >= MAX_RETRIES:
            return transfer_to_agent_twiml(AGENT_NUMBER)
        return admission_start_twiml()

    result = detect_intent(speech)
    if result["intent"] in ("cancel", "goodbye"):
        return main_menu_twiml()

    # Accept as patient name (GPT may extract entity, else use raw speech)
    patient_name = result["entities"].get("patient_name") or speech
    set_collected(call_sid, "patient_name", patient_name)
    update_session(call_sid, {"stage": "admission_ward"})
    reset_retry(call_sid)
    return admission_get_ward_twiml(patient_name)


@router.post("/admission/ward")
async def admission_ward(request: Request):
    """Step 2: Collect desired ward."""
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    speech = form.get("SpeechResult", "").strip()
    digits = form.get("Digits", "").strip()

    if not speech and not digits:
        retry = increment_retry(call_sid)
        if retry >= MAX_RETRIES:
            return transfer_to_agent_twiml(AGENT_NUMBER)
        patient_name = get_collected(call_sid, "patient_name", "the patient")
        return admission_get_ward_twiml(patient_name)

    result = detect_intent(speech or digits)
    if result["intent"] in ("cancel",):
        return main_menu_twiml()

    ward_key = result["entities"].get("ward_name")
    if not ward_key:
        retry = increment_retry(call_sid)
        if retry >= MAX_RETRIES:
            return transfer_to_agent_twiml(AGENT_NUMBER)
        patient_name = get_collected(call_sid, "patient_name", "the patient")
        return admission_get_ward_twiml(patient_name)

    # Check availability
    ward_data = get_ward_info(ward_key)
    if ward_data and ward_data["available_beds"] == 0:
        return no_beds_twiml(ward_data["name"])

    set_collected(call_sid, "ward_name", ward_key)
    update_session(call_sid, {"stage": "admission_urgency"})
    reset_retry(call_sid)
    return admission_get_urgency_twiml(ward_data["name"] if ward_data else ward_key.title())


@router.post("/admission/urgency")
async def admission_urgency(request: Request):
    """Step 3: Collect urgency level."""
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    speech = form.get("SpeechResult", "").strip()

    if not speech:
        retry = increment_retry(call_sid)
        ward_key = get_collected(call_sid, "ward_name", "general")
        ward = get_ward_info(ward_key)
        return admission_get_urgency_twiml(ward["name"] if ward else ward_key.title())

    result = detect_intent(speech)
    if result["intent"] == "cancel":
        return main_menu_twiml()

    # Extract urgency from NLU entities or raw text
    urgency = result["entities"].get("urgency")
    if not urgency:
        text_lower = speech.lower()
        if any(w in text_lower for w in ["emergency", "critical", "urgent", "serious"]):
            urgency = "emergency"
        elif any(w in text_lower for w in ["routine", "planned", "normal", "scheduled"]):
            urgency = "routine"
        else:
            urgency = "urgent"

    set_collected(call_sid, "urgency", urgency)
    update_session(call_sid, {"stage": "admission_confirm"})
    reset_retry(call_sid)

    data = {
        "patient_name": get_collected(call_sid, "patient_name"),
        "ward_name": get_collected(call_sid, "ward_name"),
        "urgency": urgency,
    }
    return admission_confirm_twiml(data)


@router.post("/admission/confirm")
async def admission_confirm(request: Request):
    """Step 4: Confirm and submit admission request."""
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    speech = form.get("SpeechResult", "").strip()
    digits = form.get("Digits", "").strip()

    result = detect_intent(speech or digits)
    intent = result["intent"]
    text_lower = (speech or digits).lower()

    is_confirmed = (
        intent == "confirm"
        or digits == "1"
        or any(w in text_lower for w in ["yes", "correct", "right", "confirm", "okay"])
    )
    is_denied = (
        intent == "deny"
        or digits == "2"
        or any(w in text_lower for w in ["no", "wrong", "change", "incorrect"])
    )

    if is_confirmed:
        data = {
            "patient_name": get_collected(call_sid, "patient_name"),
            "ward_name": get_collected(call_sid, "ward_name"),
            "urgency": get_collected(call_sid, "urgency"),
            "call_sid": call_sid,
        }
        req_id = create_admission_request(data)
        ward_info = get_ward_info(data["ward_name"]) or {}
        ward_display = ward_info.get("name", data["ward_name"].title())
        update_session(call_sid, {"stage": "admission_complete"})
        return admission_success_twiml(req_id, ward_display)

    elif is_denied:
        # Restart admission
        return admission_start_twiml()

    else:
        retry = increment_retry(call_sid)
        if retry >= MAX_RETRIES:
            return transfer_to_agent_twiml(AGENT_NUMBER)
        data = {
            "patient_name": get_collected(call_sid, "patient_name"),
            "ward_name": get_collected(call_sid, "ward_name"),
            "urgency": get_collected(call_sid, "urgency"),
        }
        return admission_confirm_twiml(data)


# Retry endpoints (redirect back to same step)
@router.post("/admission/retry-ward")
async def admission_retry_ward(request: Request):
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    patient_name = get_collected(call_sid, "patient_name", "the patient")
    return admission_get_ward_twiml(patient_name)

@router.post("/admission/retry-urgency")
async def admission_retry_urgency(request: Request):
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    ward_key = get_collected(call_sid, "ward_name", "general")
    ward = get_ward_info(ward_key)
    return admission_get_urgency_twiml(ward["name"] if ward else ward_key.title())

@router.post("/admission/retry-confirm")
async def admission_retry_confirm(request: Request):
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    data = {
        "patient_name": get_collected(call_sid, "patient_name"),
        "ward_name": get_collected(call_sid, "ward_name"),
        "urgency": get_collected(call_sid, "urgency"),
    }
    return admission_confirm_twiml(data)


# ─────────────────────────────────────────────
#  PATIENT STATUS FLOW
# ─────────────────────────────────────────────

@router.post("/patient-status-response")
async def patient_status_response(request: Request):
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    speech = form.get("SpeechResult", "").strip()

    if not speech:
        retry = increment_retry(call_sid)
        if retry >= MAX_RETRIES:
            return transfer_to_agent_twiml(AGENT_NUMBER)
        return patient_status_ask_twiml()

    result = detect_intent(speech)
    if result["intent"] == "cancel":
        return main_menu_twiml()

    pid = result["entities"].get("patient_id")
    pname = result["entities"].get("patient_name")

    if pid:
        patient = find_patient(pid)
        if patient:
            reset_retry(call_sid)
            return patient_found_twiml(patient)

    if pname:
        matches = find_patient_by_name(pname)
        if matches:
            reset_retry(call_sid)
            return patient_found_twiml(matches[0])

    # Try raw speech as patient ID
    import re
    id_match = re.search(r'[Pp]\s*(\d{4})', speech)
    if id_match:
        pid = f"P{id_match.group(1)}"
        patient = find_patient(pid)
        if patient:
            reset_retry(call_sid)
            return patient_found_twiml(patient)

    retry = increment_retry(call_sid)
    if retry >= MAX_RETRIES:
        return transfer_to_agent_twiml(AGENT_NUMBER)
    return patient_not_found_twiml()


@router.post("/patient-status-retry")
async def patient_status_retry(request: Request):
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    speech = form.get("SpeechResult", "").strip()
    digits = form.get("Digits", "").strip()

    result = detect_intent(speech or digits)
    intent = result["intent"]

    if intent == "transfer_to_agent" or "agent" in (speech.lower()):
        return transfer_to_agent_twiml(AGENT_NUMBER)
    if "main menu" in (speech.lower()) or intent == "cancel":
        return main_menu_twiml()
    return patient_status_ask_twiml()


# ─────────────────────────────────────────────
#  WARD INQUIRY FLOW
# ─────────────────────────────────────────────

@router.post("/ward-info-response")
async def ward_info_response(request: Request):
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    speech = form.get("SpeechResult", "").strip()
    digits = form.get("Digits", "").strip()

    if not speech and not digits:
        retry = increment_retry(call_sid)
        return error_reprompt_twiml(retry)

    result = detect_intent(speech or digits)
    intent = result["intent"]
    entities = result["entities"]

    if intent in ("cancel", "goodbye"):
        return goodbye_twiml()
    if intent == "patient_admission":
        return admission_start_twiml()
    if "main menu" in speech.lower():
        return main_menu_twiml()

    ward_key = entities.get("ward_name")
    if ward_key:
        set_collected(call_sid, "ward_name", ward_key)
        ward = get_ward_info(ward_key)
        return ward_info_twiml(ward)

    retry = increment_retry(call_sid)
    if retry >= MAX_RETRIES:
        return transfer_to_agent_twiml(AGENT_NUMBER)
    return ward_info_twiml()


# ─────────────────────────────────────────────
#  POST-ACTION HANDLER
# ─────────────────────────────────────────────

@router.post("/post-action")
async def post_action(request: Request):
    """After completing a task, route caller based on their choice."""
    form = await _get_form(request)
    call_sid = form.get("CallSid", "test_sid")
    speech = form.get("SpeechResult", "").strip()
    digits = form.get("Digits", "").strip()

    result = detect_intent(speech or digits)
    intent = result["intent"]
    text_lower = (speech or digits).lower()

    wants_more = (
        intent == "confirm"
        or digits == "1"
        or any(w in text_lower for w in ["yes", "more", "help", "another", "menu"])
    )

    if wants_more:
        return main_menu_twiml()
    else:
        end_session(call_sid)
        return goodbye_twiml()


# ─────────────────────────────────────────────
#  CALL STATUS CALLBACK (Twilio lifecycle)
# ─────────────────────────────────────────────

@router.post("/call-status")
async def call_status(request: Request):
    """Twilio call status webhook — cleans up session on call end."""
    form = await _get_form(request)
    call_sid = form.get("CallSid", "")
    call_status = form.get("CallStatus", "")
    logger.info(f"Call {call_sid} status: {call_status}")
    if call_status in ("completed", "failed", "busy", "no-answer", "canceled"):
        end_session(call_sid)
    return Response(content="", status_code=204)
