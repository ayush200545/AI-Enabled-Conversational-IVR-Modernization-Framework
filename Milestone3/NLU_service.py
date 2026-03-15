"""
NLU Service - OpenAI GPT-Powered Intent & Entity Detection
Handles natural language understanding for hospital IVR.

Intent Categories:
  - bed_availability      : "Are there any beds available?"
  - patient_admission     : "I want to admit a patient"
  - patient_status        : "What is the status of patient P1001?"
  - ward_inquiry          : "Tell me about the ICU ward"
  - transfer_to_agent     : "Connect me to a doctor / nurse / human"
  - repeat_menu           : "Can you repeat that?"
  - cancel / goodbye      : "Cancel", "Thank you, bye"
  - confirm               : "Yes" / "Okay" / "Correct"
  - deny                  : "No" / "That's wrong"
"""

import os
import json
import re
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

# OpenAI client — set OPENAI_API_KEY in your .env
_client = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


# ─────────────────────────────────────────────
#  SYSTEM PROMPT
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """
You are an intent and entity extractor for a Hospital IVR (Interactive Voice Response) system.
The hospital's IVR handles: Patient Admission, Bed Availability, and Ward/Department Inquiries.

Your job is to analyze caller speech transcripts and return a JSON object ONLY.

INTENTS (choose exactly one):
- bed_availability      : caller asks about available beds, vacancy, bed count
- patient_admission     : caller wants to admit a patient, register a new patient
- patient_status        : caller asks about a specific patient's condition or location
- ward_inquiry          : caller asks about a specific ward, department, or specialty
- transfer_to_agent     : caller wants to speak to a human, doctor, nurse, or staff
- repeat_menu           : caller wants options repeated
- confirm               : caller is confirming something (yes, okay, correct, right, haan)
- deny                  : caller is rejecting something (no, nahi, wrong, incorrect)
- cancel                : caller wants to cancel or go back to main menu
- goodbye               : caller is ending the call
- unknown               : cannot determine intent

ENTITIES (extract if present, else null):
- ward_name      : one of [general, icu, emergency, pediatric, maternity, cardiology, orthopedic, neurology]
- patient_id     : format like P1001, P1002 (patient ID number)
- patient_name   : full or partial name of a patient
- date           : any mentioned date
- urgency        : "emergency", "urgent", or "routine" — infer from context

Return ONLY this JSON (no markdown, no preamble):
{
  "intent": "<intent>",
  "confidence": <0.0 to 1.0>,
  "entities": {
    "ward_name": null,
    "patient_id": null,
    "patient_name": null,
    "date": null,
    "urgency": null
  },
  "interpreted_as": "<brief plain-English summary of what caller wants>"
}
""".strip()


# ─────────────────────────────────────────────
#  WARD NAME NORMALISER
# ─────────────────────────────────────────────

WARD_ALIASES = {
    "general ward": "general", "general": "general",
    "icu": "icu", "intensive care": "icu", "intensive care unit": "icu",
    "emergency": "emergency", "casualty": "emergency", "accident": "emergency",
    "pediatric": "pediatric", "paediatric": "pediatric", "children": "pediatric", "child ward": "pediatric",
    "maternity": "maternity", "labour": "maternity", "delivery": "maternity", "gynae": "maternity",
    "cardiology": "cardiology", "cardiac": "cardiology", "heart": "cardiology",
    "orthopedic": "orthopedic", "orthopaedic": "orthopedic", "bone": "orthopedic",
    "neurology": "neurology", "neuro": "neurology", "brain": "neurology",
}

def normalise_ward(raw: str | None) -> str | None:
    if not raw:
        return None
    raw_lower = raw.lower().strip()
    for alias, canonical in WARD_ALIASES.items():
        if alias in raw_lower:
            return canonical
    return None


# ─────────────────────────────────────────────
#  MAIN DETECT FUNCTION
# ─────────────────────────────────────────────

def detect_intent(speech_text: str, confidence_score: float = 1.0) -> dict:
    """
    Detect intent and entities from caller speech.
    Falls back to keyword matching if OpenAI fails or confidence too low.

    Returns:
        {
            "intent": str,
            "confidence": float,
            "entities": dict,
            "interpreted_as": str,
            "source": "gpt" | "fallback"
        }
    """
    if not speech_text or not speech_text.strip():
        return _empty_result()

    text = speech_text.strip()

    # ── Try GPT first ──────────────────────────────────────
    try:
        result = _gpt_detect(text)
        result["source"] = "gpt"
        # Normalise ward entity
        if result["entities"].get("ward_name"):
            result["entities"]["ward_name"] = normalise_ward(result["entities"]["ward_name"])
        return result
    except Exception as e:
        logger.warning(f"GPT intent detection failed: {e}. Falling back to keyword matching.")
        return _keyword_fallback(text)


def _gpt_detect(text: str) -> dict:
    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Caller said: \"{text}\""}
        ],
        max_tokens=300,
    )
    raw = response.choices[0].message.content.strip()
    # Strip markdown fences if present
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    return json.loads(raw)


# ─────────────────────────────────────────────
#  KEYWORD FALLBACK (no API needed)
# ─────────────────────────────────────────────

_KEYWORD_MAP = {
    "bed_availability": [
        "bed", "beds", "available", "availability", "vacancy",
        "empty", "free bed", "how many beds", "vacant"
    ],
    "patient_admission": [
        "admit", "admission", "register", "new patient", "book bed",
        "hospitalise", "hospitalize", "want to admit", "need to admit"
    ],
    "patient_status": [
        "status", "condition", "where is", "which ward", "patient",
        "update on", "information about", "how is"
    ],
    "ward_inquiry": [
        "ward", "icu", "emergency", "cardiology", "neurology",
        "pediatric", "maternity", "orthopedic", "department", "floor",
        "tell me about", "information about ward"
    ],
    "transfer_to_agent": [
        "human", "agent", "doctor", "nurse", "staff", "operator",
        "speak to", "connect me", "transfer", "real person"
    ],
    "repeat_menu": [
        "repeat", "again", "pardon", "what", "say again", "options"
    ],
    "confirm": [
        "yes", "yeah", "correct", "right", "okay", "ok",
        "confirm", "sure", "haan", "ji haan", "bilkul"
    ],
    "deny": [
        "no", "nope", "wrong", "incorrect", "nahi", "na",
        "not right", "that's wrong"
    ],
    "goodbye": [
        "bye", "goodbye", "thank you", "thanks", "that's all",
        "no more help", "end call", "disconnect"
    ],
    "cancel": [
        "cancel", "go back", "main menu", "start over", "restart"
    ],
}

def _keyword_fallback(text: str) -> dict:
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for intent, keywords in _KEYWORD_MAP.items():
        scores[intent] = sum(1 for kw in keywords if kw in text_lower)

    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    if best_score == 0:
        best_intent = "unknown"
        conf = 0.3
    else:
        conf = min(0.5 + (best_score * 0.1), 0.85)

    # Simple entity extraction
    entities = {
        "ward_name": _extract_ward(text_lower),
        "patient_id": _extract_patient_id(text),
        "patient_name": None,
        "date": None,
        "urgency": _extract_urgency(text_lower),
    }

    return {
        "intent": best_intent,
        "confidence": conf,
        "entities": entities,
        "interpreted_as": f"Caller mentioned: {text[:80]}",
        "source": "fallback"
    }


def _extract_ward(text: str) -> str | None:
    for alias, canonical in WARD_ALIASES.items():
        if alias in text:
            return canonical
    return None

def _extract_patient_id(text: str) -> str | None:
    match = re.search(r'\bP\d{4}\b', text, re.IGNORECASE)
    return match.group(0).upper() if match else None

def _extract_urgency(text: str) -> str | None:
    if any(w in text for w in ["emergency", "urgent", "critical", "serious", "immediately"]):
        return "emergency"
    if any(w in text for w in ["soon", "as soon as possible", "asap", "today"]):
        return "urgent"
    return None

def _empty_result() -> dict:
    return {
        "intent": "unknown",
        "confidence": 0.0,
        "entities": {"ward_name": None, "patient_id": None, "patient_name": None, "date": None, "urgency": None},
        "interpreted_as": "No speech detected",
        "source": "empty"
    }
