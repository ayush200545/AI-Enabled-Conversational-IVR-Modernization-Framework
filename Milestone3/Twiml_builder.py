"""
TwiML Builder - Hospital IVR Response Generator
Generates all TwiML XML responses with Polly voice, SSML, and proper hints.
"""

from fastapi.responses import Response

VOICE = "Polly.Aditi"          # Indian female voice
LANGUAGE = "en-IN"

# ─────────────────────────────────────────────
#  SPEECH RECOGNITION HINTS
# ─────────────────────────────────────────────

HOSPITAL_HINTS = (
    "bed availability,admit,admission,patient status,ward inquiry,"
    "general ward,ICU,intensive care,emergency,pediatric,maternity,"
    "cardiology,neurology,orthopedic,yes,no,cancel,transfer,doctor,"
    "nurse,agent,patient ID,P1001,P1002,P1003,P1004"
)

WARD_HINTS = (
    "general ward,ICU,intensive care,emergency,pediatric,maternity,"
    "cardiology,neurology,orthopedic,bone ward,heart ward,children ward"
)

CONFIRM_HINTS = "yes,no,correct,wrong,okay,cancel,repeat"

PATIENT_ID_HINTS = "P1001,P1002,P1003,P1004,patient ID"


# ─────────────────────────────────────────────
#  LOW-LEVEL HELPERS
# ─────────────────────────────────────────────

def twiml_response(content: str) -> Response:
    return Response(
        content=f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n{content}\n</Response>',
        media_type="application/xml"
    )

def say(text: str, voice: str = VOICE, language: str = LANGUAGE) -> str:
    return f'  <Say voice="{voice}" language="{language}">{text}</Say>'

def gather_speech(action: str, hints: str = HOSPITAL_HINTS, timeout: int = 5) -> str:
    return (
        f'  <Gather input="dtmf speech" action="{action}" '
        f'language="{LANGUAGE}" speechTimeout="auto" '
        f'hints="{hints}" timeout="{timeout}">'
    )

def gather_close() -> str:
    return "  </Gather>"

def hangup() -> str:
    return "  <Hangup/>"

def dial(number: str) -> str:
    return f'  <Dial>{number}</Dial>'

def pause(length: int = 1) -> str:
    return f'  <Pause length="{length}"/>'

def redirect(url: str) -> str:
    return f'  <Redirect>{url}</Redirect>'


# ─────────────────────────────────────────────
#  SSML HELPERS
# ─────────────────────────────────────────────

def spell(text: str) -> str:
    """Spell out characters one by one."""
    return f'<say-as interpret-as="spell-out">{text}</say-as>'

def break_ms(ms: int) -> str:
    return f'<break time="{ms}ms"/>'

def emphasis(text: str, level: str = "moderate") -> str:
    return f'<emphasis level="{level}">{text}</emphasis>'

def prosody(text: str, rate: str = "medium", pitch: str = "medium") -> str:
    return f'<prosody rate="{rate}" pitch="{pitch}">{text}</prosody>'


# ─────────────────────────────────────────────
#  FULL TWIML BUILDERS
# ─────────────────────────────────────────────

def welcome_twiml() -> Response:
    body = "\n".join([
        gather_speech("/ivr/intent", hints=HOSPITAL_HINTS),
        say(
            f"Welcome to City General Hospital. {break_ms(300)} "
            "I can help you with bed availability, patient admission, "
            f"ward information, or patient status. {break_ms(400)} "
            "How may I assist you today?"
        ),
        gather_close(),
        # No-speech fallback
        say("I didn't catch that. Let me repeat the options."),
        redirect("/ivr/welcome"),
    ])
    return twiml_response(body)


def main_menu_twiml(reprompt: bool = False) -> Response:
    intro = "Sorry, I didn't understand. Let me give you the main menu." if reprompt else ""
    options = (
        f"{intro} {break_ms(200)}"
        "Please say or press a number. "
        f"{break_ms(300)}"
        "For bed availability, say 'bed availability' or press 1. "
        f"{break_ms(200)}"
        "For patient admission, say 'admission' or press 2. "
        f"{break_ms(200)}"
        "For patient status, say 'patient status' or press 3. "
        f"{break_ms(200)}"
        "For ward information, say 'ward inquiry' or press 4. "
        f"{break_ms(200)}"
        "To speak to our staff, say 'agent' or press 0."
    )
    body = "\n".join([
        gather_speech("/ivr/intent", hints=HOSPITAL_HINTS),
        say(options),
        gather_close(),
        redirect("/ivr/welcome"),
    ])
    return twiml_response(body)


def bed_availability_twiml(ward_data: dict | None = None, ward_name: str | None = None) -> Response:
    if ward_data and ward_name:
        # Specific ward result
        w = ward_data
        avail = w["available_beds"]
        total = w["total_beds"]
        occ = w["occupancy_rate"]
        status_word = "available" if avail > 0 else "no beds available"
        urgent_note = (
            f"{break_ms(300)} Please note: This ward has {emphasis('very limited availability', 'strong')}."
            if avail <= 2 else ""
        )
        message = (
            f"Bed availability for {emphasis(w['name'], 'moderate')}. "
            f"{break_ms(400)}"
            f"Total beds: {total}. "
            f"Currently {status_word}: {avail} beds. "
            f"Occupancy rate: {occ} percent. "
            f"Located on the {w['floor']}. "
            f"For direct inquiries, call extension {spell(w['contact_ext'])}."
            f"{urgent_note}"
            f"{break_ms(500)}"
            "Would you like to check another ward, proceed to admission, or return to the main menu? "
            "Say 'another ward', 'admission', or 'main menu'."
        )
    else:
        # Ask which ward
        message = (
            "I can check bed availability for you. "
            f"{break_ms(300)}"
            "Which ward would you like to check? "
            f"{break_ms(200)}"
            "You can say: General Ward, ICU, Emergency, Pediatric, "
            "Maternity, Cardiology, Orthopedic, or Neurology. "
            f"{break_ms(200)}"
            "Or say 'all wards' for a complete overview."
        )

    body = "\n".join([
        gather_speech("/ivr/bed-availability-response", hints=WARD_HINTS + ",all wards,admission,main menu,another ward"),
        say(message),
        gather_close(),
        say("I didn't hear a response. Returning to the main menu."),
        redirect("/ivr/menu"),
    ])
    return twiml_response(body)


def all_beds_summary_twiml(stats: dict, available_wards: list) -> Response:
    avail_names = ", ".join(w["name"] for w in available_wards[:4])
    more = f"and {len(available_wards) - 4} more" if len(available_wards) > 4 else ""
    message = (
        f"Hospital-wide bed status. {break_ms(400)}"
        f"Total beds: {stats['total_beds']}. "
        f"Available beds: {emphasis(str(stats['available_beds']), 'moderate')}. "
        f"Current occupancy: {stats['occupancy_rate']} percent. "
        f"{break_ms(300)}"
        f"Wards with available beds include: {avail_names}{' ' + more if more else ''}. "
        f"{break_ms(400)}"
        "To check a specific ward, please say the ward name. "
        "Or say 'admission' to begin the admission process."
    )
    body = "\n".join([
        gather_speech("/ivr/bed-availability-response", hints=WARD_HINTS + ",admission,main menu"),
        say(message),
        gather_close(),
        redirect("/ivr/menu"),
    ])
    return twiml_response(body)


def admission_start_twiml() -> Response:
    message = (
        "I'll help you with patient admission. "
        f"{break_ms(400)}"
        "Please listen carefully. I'll collect some basic information. "
        f"{break_ms(300)}"
        "First, please say the full name of the patient to be admitted."
    )
    body = "\n".join([
        gather_speech("/ivr/admission/name",
                      hints="patient name,first name,full name,cancel",
                      timeout=8),
        say(message),
        gather_close(),
        say("I didn't hear the patient name. Returning to the main menu."),
        redirect("/ivr/menu"),
    ])
    return twiml_response(body)


def admission_get_ward_twiml(patient_name: str) -> Response:
    message = (
        f"Thank you. Patient name noted as: {prosody(patient_name, rate='slow')}. "
        f"{break_ms(400)}"
        "Which ward do you require admission to? "
        f"{break_ms(200)}"
        "Available options: General Ward, ICU, Emergency, Pediatric, "
        "Maternity, Cardiology, Orthopedic, or Neurology."
    )
    body = "\n".join([
        gather_speech("/ivr/admission/ward", hints=WARD_HINTS + ",cancel"),
        say(message),
        gather_close(),
        say("I didn't hear a ward selection. Let me ask again."),
        redirect("/ivr/admission/retry-ward"),
    ])
    return twiml_response(body)


def admission_get_urgency_twiml(ward_name: str) -> Response:
    message = (
        f"Admission to {ward_name} noted. "
        f"{break_ms(300)}"
        "What is the urgency level? "
        f"{break_ms(200)}"
        "Say 'emergency' for critical or life-threatening cases, "
        "'urgent' for serious but stable cases, "
        "or 'routine' for planned admission."
    )
    body = "\n".join([
        gather_speech("/ivr/admission/urgency",
                      hints="emergency,urgent,routine,critical,stable,planned,cancel"),
        say(message),
        gather_close(),
        redirect("/ivr/admission/retry-urgency"),
    ])
    return twiml_response(body)


def admission_confirm_twiml(data: dict) -> Response:
    name = data.get("patient_name", "Unknown")
    ward = data.get("ward_name", "General Ward").title()
    urgency = data.get("urgency", "routine").title()
    message = (
        f"Please confirm the following admission request. "
        f"{break_ms(500)}"
        f"Patient name: {prosody(name, rate='slow')}. "
        f"{break_ms(200)}"
        f"Ward: {ward}. "
        f"{break_ms(200)}"
        f"Urgency: {urgency}. "
        f"{break_ms(500)}"
        "Is this information correct? Say 'yes' to confirm or 'no' to make changes."
    )
    body = "\n".join([
        gather_speech("/ivr/admission/confirm",
                      hints=CONFIRM_HINTS, timeout=6),
        say(message),
        gather_close(),
        redirect("/ivr/admission/retry-confirm"),
    ])
    return twiml_response(body)


def admission_success_twiml(req_id: str, ward_name: str) -> Response:
    message = (
        f"Your admission request has been {emphasis('successfully submitted', 'strong')}. "
        f"{break_ms(500)}"
        f"Your reference number is: {spell(req_id)}. "
        f"{break_ms(300)}"
        "Please note this reference number for future correspondence. "
        f"{break_ms(400)}"
        f"Our {ward_name} team will contact you within 30 minutes to confirm the bed assignment. "
        f"{break_ms(300)}"
        "Is there anything else I can help you with? "
        "Say 'yes' to return to the main menu or 'no' to end the call."
    )
    body = "\n".join([
        gather_speech("/ivr/post-action", hints=CONFIRM_HINTS),
        say(message),
        gather_close(),
        say("Thank you for calling City General Hospital. We wish you good health. Goodbye."),
        hangup(),
    ])
    return twiml_response(body)


def patient_status_ask_twiml() -> Response:
    message = (
        "I can provide a patient status update. "
        f"{break_ms(300)}"
        "Please say the patient ID, for example P-1-0-0-1, "
        "or say the patient's full name."
    )
    body = "\n".join([
        gather_speech("/ivr/patient-status-response",
                      hints=PATIENT_ID_HINTS + ",patient name,cancel",
                      timeout=7),
        say(message),
        gather_close(),
        say("I didn't hear a patient ID. Returning to the main menu."),
        redirect("/ivr/menu"),
    ])
    return twiml_response(body)


def patient_found_twiml(patient: dict) -> Response:
    name = patient["name"]
    ward = patient["ward"].title()
    bed = patient["bed_number"]
    doctor = patient["doctor"]
    status = patient["status"]
    date = patient["admission_date"]
    diagnosis = patient["diagnosis"]
    message = (
        f"Patient information found. {break_ms(400)}"
        f"Name: {prosody(name, rate='slow')}. {break_ms(200)}"
        f"Status: {emphasis(status, 'moderate')}. {break_ms(200)}"
        f"Ward: {ward} Ward. {break_ms(200)}"
        f"Bed number: {spell(bed)}. {break_ms(200)}"
        f"Admitted on: {date}. {break_ms(200)}"
        f"Attending doctor: {doctor}. {break_ms(200)}"
        f"Diagnosis notes: {diagnosis}. {break_ms(400)}"
        "Is there anything else I can help you with? "
        "Say 'yes' for main menu or 'no' to end the call."
    )
    body = "\n".join([
        gather_speech("/ivr/post-action", hints=CONFIRM_HINTS),
        say(message),
        gather_close(),
        say("Thank you for calling City General Hospital. Goodbye."),
        hangup(),
    ])
    return twiml_response(body)


def patient_not_found_twiml() -> Response:
    message = (
        "I'm sorry, I could not find a patient matching that information. "
        f"{break_ms(300)}"
        "Please double-check the patient ID or name. "
        f"{break_ms(400)}"
        "Would you like to try again, or speak to a staff member? "
        "Say 'try again', 'agent', or 'main menu'."
    )
    body = "\n".join([
        gather_speech("/ivr/patient-status-retry",
                      hints="try again,agent,main menu,cancel"),
        say(message),
        gather_close(),
        redirect("/ivr/menu"),
    ])
    return twiml_response(body)


def ward_info_twiml(ward: dict | None = None) -> Response:
    if ward:
        avail = ward["available_beds"]
        avail_text = f"{avail} bed{'s' if avail != 1 else ''} available" if avail > 0 else "no beds currently available"
        message = (
            f"Information for {emphasis(ward['name'], 'moderate')}. "
            f"{break_ms(400)}"
            f"Speciality: {ward['speciality']}. {break_ms(200)}"
            f"Location: {ward['floor']}. {break_ms(200)}"
            f"Total capacity: {ward['total_beds']} beds. {break_ms(200)}"
            f"Current availability: {avail_text}. {break_ms(200)}"
            f"Contact extension: {spell(ward['contact_ext'])}. {break_ms(400)}"
            "Would you like to know about another ward, check admission, or return to main menu?"
        )
    else:
        message = (
            "Which ward or department would you like information about? "
            f"{break_ms(200)}"
            "You can say: General Ward, ICU, Emergency, Pediatric, "
            "Maternity, Cardiology, Orthopedic, or Neurology."
        )
    body = "\n".join([
        gather_speech("/ivr/ward-info-response",
                      hints=WARD_HINTS + ",admission,main menu,another ward"),
        say(message),
        gather_close(),
        redirect("/ivr/menu"),
    ])
    return twiml_response(body)


def transfer_to_agent_twiml(agent_number: str = "+919800000000") -> Response:
    body = "\n".join([
        say(
            "Please hold while I transfer you to our hospital staff. "
            f"{break_ms(600)}"
            "Thank you for your patience."
        ),
        pause(2),
        dial(agent_number),
        # Fallback if dial fails
        say(
            "I'm sorry, all our staff are currently busy. "
            "Please call back or visit us at the reception. Goodbye."
        ),
        hangup(),
    ])
    return twiml_response(body)


def error_reprompt_twiml(attempt: int) -> Response:
    if attempt == 1:
        msg = "I'm sorry, I didn't quite catch that. Could you please repeat?"
    elif attempt == 2:
        msg = "I'm still having trouble understanding. Please speak clearly after the tone."
    else:
        msg = (
            "I'm having difficulty understanding your request. "
            "Let me transfer you to a staff member for assistance."
        )
    body = "\n".join([
        say(msg),
        redirect("/ivr/menu" if attempt >= 3 else "/ivr/welcome"),
    ])
    return twiml_response(body)


def goodbye_twiml() -> Response:
    body = "\n".join([
        say(
            "Thank you for calling City General Hospital. "
            f"{break_ms(300)}"
            "We are dedicated to your health and well-being. "
            f"{break_ms(300)}"
            "Have a great day. Goodbye!"
        ),
        hangup(),
    ])
    return twiml_response(body)


def no_beds_twiml(ward_name: str) -> Response:
    message = (
        f"I'm sorry, there are currently {emphasis('no available beds', 'strong')} "
        f"in the {ward_name}. "
        f"{break_ms(400)}"
        "Would you like to check another ward, or speak to an admission counsellor "
        "who may be able to assist with alternative arrangements? "
        "Say 'another ward' or 'agent'."
    )
    body = "\n".join([
        gather_speech("/ivr/bed-availability-response",
                      hints=WARD_HINTS + ",another ward,agent,main menu"),
        say(message),
        gather_close(),
        redirect("/ivr/menu"),
    ])
    return twiml_response(body)
