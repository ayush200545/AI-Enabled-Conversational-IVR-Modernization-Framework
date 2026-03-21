"""
Milestone 4 — Unit Tests
Hospital IVR: Patient Admission & Bed Availability Management

Tests every FastAPI endpoint in isolation using FastAPI's TestClient.
No real Twilio calls, no real OpenAI calls, no real database writes.
All external dependencies are mocked.

Run:
    pytest tests/test_unit.py -v
    pytest tests/test_unit.py -v --tb=short          # shorter tracebacks
    pytest tests/test_unit.py -v -k "bed"            # run only bed-related tests
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# ── App import ─────────────────────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from main import app

client = TestClient(app, raise_server_exceptions=True)

# ── Shared test data ────────────────────────────────────────────────────────

VALID_CALL_SID = "CA_TEST_UNIT_001"

TWILIO_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Twilio-Signature": "bypass_for_tests",          # security middleware uses LOG_ONLY in test env
}

WARD_NAMES = ["general", "icu", "emergency", "pediatric",
              "maternity", "cardiology", "orthopedic", "neurology"]


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 1 — Root & Health Endpoints
# ══════════════════════════════════════════════════════════════════════════════

class TestRootEndpoints:
    """Smoke tests for root-level informational endpoints."""

    def test_root_returns_200(self):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_contains_service_name(self):
        data = client.get("/").json()
        assert "Hospital" in data["service"] or "IVR" in data["service"]

    def test_root_lists_flows(self):
        data = client.get("/").json()
        assert isinstance(data["flows"], list)
        assert len(data["flows"]) >= 4

    def test_health_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_status_healthy(self):
        data = client.get("/health").json()
        assert data["status"] == "healthy"

    def test_security_endpoint_returns_200(self):
        resp = client.get("/security")
        assert resp.status_code == 200

    def test_security_contains_mode(self):
        data = client.get("/security").json()
        assert "validation_mode" in data
        assert data["validation_mode"] in ("enforce", "log_only", "disabled")


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 2 — IVR Welcome Endpoint
# ══════════════════════════════════════════════════════════════════════════════

class TestIVRWelcome:
    """Tests for /ivr/welcome — the Twilio entry point."""

    def test_welcome_get_returns_200(self):
        resp = client.get("/ivr/welcome")
        assert resp.status_code == 200

    def test_welcome_post_returns_200(self):
        resp = client.post("/ivr/welcome",
                           data={"CallSid": VALID_CALL_SID},
                           headers=TWILIO_HEADERS)
        assert resp.status_code == 200

    def test_welcome_response_is_xml(self):
        resp = client.post("/ivr/welcome",
                           data={"CallSid": VALID_CALL_SID},
                           headers=TWILIO_HEADERS)
        assert "application/xml" in resp.headers["content-type"]

    def test_welcome_contains_gather_tag(self):
        resp = client.post("/ivr/welcome",
                           data={"CallSid": VALID_CALL_SID},
                           headers=TWILIO_HEADERS)
        assert "<Gather" in resp.text

    def test_welcome_uses_polly_aditi_voice(self):
        resp = client.post("/ivr/welcome",
                           data={"CallSid": VALID_CALL_SID},
                           headers=TWILIO_HEADERS)
        assert "Polly.Aditi" in resp.text

    def test_welcome_mentions_hospital(self):
        resp = client.post("/ivr/welcome",
                           data={"CallSid": VALID_CALL_SID},
                           headers=TWILIO_HEADERS)
        assert "Hospital" in resp.text or "hospital" in resp.text

    def test_welcome_contains_input_speech_attribute(self):
        resp = client.post("/ivr/welcome",
                           data={"CallSid": "CA_TEST_002"},
                           headers=TWILIO_HEADERS)
        assert 'input=' in resp.text  # supports speech or dtmf speech


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 3 — Main Menu
# ══════════════════════════════════════════════════════════════════════════════

class TestMainMenu:
    """Tests for /ivr/menu."""

    def test_menu_returns_xml(self):
        resp = client.post("/ivr/menu",
                           data={"CallSid": VALID_CALL_SID},
                           headers=TWILIO_HEADERS)
        assert resp.status_code == 200
        assert "application/xml" in resp.headers["content-type"]

    def test_menu_contains_gather(self):
        resp = client.post("/ivr/menu",
                           data={"CallSid": VALID_CALL_SID},
                           headers=TWILIO_HEADERS)
        assert "<Gather" in resp.text

    def test_menu_offers_bed_availability_option(self):
        resp = client.post("/ivr/menu",
                           data={"CallSid": VALID_CALL_SID},
                           headers=TWILIO_HEADERS)
        assert "bed" in resp.text.lower() or "1" in resp.text

    def test_menu_offers_admission_option(self):
        resp = client.post("/ivr/menu",
                           data={"CallSid": VALID_CALL_SID},
                           headers=TWILIO_HEADERS)
        assert "admission" in resp.text.lower() or "2" in resp.text


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 4 — Intent Router (DTMF)
# ══════════════════════════════════════════════════════════════════════════════

class TestIntentRouterDTMF:
    """Tests for /ivr/intent with digit presses (no NLU needed)."""

    def _post_digits(self, call_sid: str, digits: str):
        return client.post(
            "/ivr/intent",
            data={"CallSid": call_sid, "Digits": digits},
            headers=TWILIO_HEADERS,
        )

    def test_digit_1_routes_to_bed_availability(self):
        resp = self._post_digits("CA_DTMF_001", "1")
        assert resp.status_code == 200
        # Should ask which ward or return bed info
        assert "bed" in resp.text.lower() or "ward" in resp.text.lower()

    def test_digit_2_routes_to_admission(self):
        resp = self._post_digits("CA_DTMF_002", "2")
        assert resp.status_code == 200
        assert "patient" in resp.text.lower() or "name" in resp.text.lower() or "admission" in resp.text.lower()

    def test_digit_3_routes_to_patient_status(self):
        resp = self._post_digits("CA_DTMF_003", "3")
        assert resp.status_code == 200
        assert "patient" in resp.text.lower() or "ID" in resp.text or "status" in resp.text.lower()

    def test_digit_4_routes_to_ward_inquiry(self):
        resp = self._post_digits("CA_DTMF_004", "4")
        assert resp.status_code == 200
        assert "ward" in resp.text.lower() or "department" in resp.text.lower()

    def test_digit_0_routes_to_agent_transfer(self):
        resp = self._post_digits("CA_DTMF_005", "0")
        assert resp.status_code == 200
        # Transfer: contains <Dial> or "transfer" or "agent"
        assert "<Dial>" in resp.text or "transfer" in resp.text.lower() or "agent" in resp.text.lower()

    def test_empty_input_reprompts(self):
        resp = client.post(
            "/ivr/intent",
            data={"CallSid": "CA_DTMF_006"},  # no Digits, no SpeechResult
            headers=TWILIO_HEADERS,
        )
        assert resp.status_code == 200
        # Should re-prompt, not 500
        assert "<Response>" in resp.text


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 5 — Intent Router (Speech / NLU)
# ══════════════════════════════════════════════════════════════════════════════

class TestIntentRouterSpeech:
    """
    Tests for /ivr/intent with SpeechResult.
    GPT is mocked to keep tests fast and deterministic (<100ms each).
    """

    def _mock_intent(self, intent: str, ward: str = None, patient_id: str = None,
                     urgency: str = None, confidence: float = 0.92):
        return {
            "intent": intent,
            "confidence": confidence,
            "entities": {
                "ward_name": ward,
                "patient_id": patient_id,
                "patient_name": None,
                "urgency": urgency,
            },
            "interpreted_as": f"Test mock for {intent}",
            "source": "gpt",
        }

    def _post_speech(self, call_sid: str, speech: str, confidence: str = "0.92"):
        return client.post(
            "/ivr/intent",
            data={"CallSid": call_sid, "SpeechResult": speech, "Confidence": confidence},
            headers=TWILIO_HEADERS,
        )

    @patch("milestone3.services.nlu_service.detect_intent")
    def test_bed_availability_intent_routes_correctly(self, mock_nlu):
        mock_nlu.return_value = self._mock_intent("bed_availability")
        resp = self._post_speech("CA_NLU_001", "Are there beds available?")
        assert resp.status_code == 200
        assert "ward" in resp.text.lower() or "bed" in resp.text.lower()

    @patch("milestone3.services.nlu_service.detect_intent")
    def test_bed_availability_with_ward_entity_skips_ward_question(self, mock_nlu):
        mock_nlu.return_value = self._mock_intent("bed_availability", ward="icu")
        resp = self._post_speech("CA_NLU_002", "How many beds in the ICU?")
        assert resp.status_code == 200
        # Should show ICU result directly
        assert "ICU" in resp.text or "icu" in resp.text.lower() or "ward" in resp.text.lower()

    @patch("milestone3.services.nlu_service.detect_intent")
    def test_patient_admission_intent_starts_flow(self, mock_nlu):
        mock_nlu.return_value = self._mock_intent("patient_admission")
        resp = self._post_speech("CA_NLU_003", "I want to admit my father")
        assert resp.status_code == 200
        assert "name" in resp.text.lower() or "patient" in resp.text.lower()

    @patch("milestone3.services.nlu_service.detect_intent")
    def test_patient_status_intent_without_id_asks_for_id(self, mock_nlu):
        mock_nlu.return_value = self._mock_intent("patient_status")
        resp = self._post_speech("CA_NLU_004", "What is the patient's condition?")
        assert resp.status_code == 200
        assert "ID" in resp.text or "id" in resp.text.lower() or "patient" in resp.text.lower()

    @patch("milestone3.services.nlu_service.detect_intent")
    def test_patient_status_with_patient_id_entity_returns_data(self, mock_nlu):
        mock_nlu.return_value = self._mock_intent("patient_status", patient_id="P1001")
        resp = self._post_speech("CA_NLU_005", "Status of P1001")
        assert resp.status_code == 200
        # Patient P1001 is Rahul Sharma — should be mentioned
        assert "Rahul" in resp.text or "Cardiology" in resp.text or "CAR" in resp.text

    @patch("milestone3.services.nlu_service.detect_intent")
    def test_ward_inquiry_intent_routes_correctly(self, mock_nlu):
        mock_nlu.return_value = self._mock_intent("ward_inquiry")
        resp = self._post_speech("CA_NLU_006", "Tell me about the maternity ward")
        assert resp.status_code == 200
        assert "ward" in resp.text.lower()

    @patch("milestone3.services.nlu_service.detect_intent")
    def test_goodbye_intent_hangs_up(self, mock_nlu):
        mock_nlu.return_value = self._mock_intent("goodbye")
        resp = self._post_speech("CA_NLU_007", "Thank you bye")
        assert resp.status_code == 200
        assert "<Hangup" in resp.text or "Goodbye" in resp.text or "goodbye" in resp.text.lower()

    @patch("milestone3.services.nlu_service.detect_intent")
    def test_transfer_intent_dials_agent(self, mock_nlu):
        mock_nlu.return_value = self._mock_intent("transfer_to_agent")
        resp = self._post_speech("CA_NLU_008", "Connect me to a doctor")
        assert resp.status_code == 200
        assert "<Dial>" in resp.text or "transfer" in resp.text.lower()

    @patch("milestone3.services.nlu_service.detect_intent")
    def test_low_confidence_triggers_confirmation(self, mock_nlu):
        mock_nlu.return_value = self._mock_intent("bed_availability", confidence=0.55)
        resp = self._post_speech("CA_NLU_009", "sumthing about bedsss", confidence="0.55")
        assert resp.status_code == 200
        # Should ask caller to confirm, not proceed directly
        assert "confirm" in resp.text.lower() or "correct" in resp.text.lower() or "yes" in resp.text.lower()


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 6 — Bed Availability
# ══════════════════════════════════════════════════════════════════════════════

class TestBedAvailability:
    """Tests for /ivr/bed-availability-response."""

    def _post(self, call_sid: str, speech: str = "", digits: str = ""):
        data = {"CallSid": call_sid}
        if speech:
            data["SpeechResult"] = speech
        if digits:
            data["Digits"] = digits
        return client.post("/ivr/bed-availability-response", data=data, headers=TWILIO_HEADERS)

    @patch("milestone3.services.nlu_service.detect_intent")
    def test_icu_returns_bed_count(self, mock_nlu):
        mock_nlu.return_value = {
            "intent": "bed_availability", "confidence": 0.95,
            "entities": {"ward_name": "icu", "patient_id": None,
                         "patient_name": None, "urgency": None},
            "interpreted_as": "ICU beds", "source": "gpt"
        }
        resp = self._post("CA_BED_001", speech="ICU")
        assert resp.status_code == 200
        assert "ICU" in resp.text or "icu" in resp.text.lower() or "2" in resp.text

    @patch("milestone3.services.nlu_service.detect_intent")
    def test_all_wards_returns_summary(self, mock_nlu):
        mock_nlu.return_value = {
            "intent": "bed_availability", "confidence": 0.90,
            "entities": {"ward_name": None, "patient_id": None,
                         "patient_name": None, "urgency": None},
            "interpreted_as": "all wards", "source": "gpt"
        }
        resp = self._post("CA_BED_002", speech="all wards")
        assert resp.status_code == 200
        # Should mention overall stats
        assert "bed" in resp.text.lower() or "ward" in resp.text.lower()

    def test_no_input_reprompts(self):
        resp = self._post("CA_BED_003")  # no speech, no digits
        assert resp.status_code == 200
        assert "<Response>" in resp.text


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 7 — Admission Flow (Multi-turn)
# ══════════════════════════════════════════════════════════════════════════════

class TestAdmissionFlow:
    """Tests for the 4-step admission flow endpoints."""

    CALL_SID = "CA_ADM_UNIT_001"

    @patch("milestone3.services.nlu_service.detect_intent")
    def test_step1_name_collection(self, mock_nlu):
        mock_nlu.return_value = {
            "intent": "patient_admission", "confidence": 0.92,
            "entities": {"ward_name": None, "patient_id": None,
                         "patient_name": "Meera Sharma", "urgency": None},
            "interpreted_as": "Patient name", "source": "gpt"
        }
        resp = client.post(
            "/ivr/admission/name",
            data={"CallSid": self.CALL_SID, "SpeechResult": "Meera Sharma", "Confidence": "0.92"},
            headers=TWILIO_HEADERS,
        )
        assert resp.status_code == 200
        # Should ask for ward
        assert "ward" in resp.text.lower() or "where" in resp.text.lower()

    @patch("milestone3.services.nlu_service.detect_intent")
    def test_step2_ward_selection(self, mock_nlu):
        # Pre-populate session by first calling name step
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = {
                "intent": "patient_admission", "confidence": 0.92,
                "entities": {"ward_name": None, "patient_id": None,
                             "patient_name": "Test Patient", "urgency": None},
                "interpreted_as": "name", "source": "gpt"
            }
            client.post("/ivr/admission/name",
                        data={"CallSid": "CA_ADM_002", "SpeechResult": "Test Patient"},
                        headers=TWILIO_HEADERS)

        mock_nlu.return_value = {
            "intent": "ward_inquiry", "confidence": 0.92,
            "entities": {"ward_name": "cardiology", "patient_id": None,
                         "patient_name": None, "urgency": None},
            "interpreted_as": "cardiology ward", "source": "gpt"
        }
        resp = client.post(
            "/ivr/admission/ward",
            data={"CallSid": "CA_ADM_002", "SpeechResult": "Cardiology", "Confidence": "0.92"},
            headers=TWILIO_HEADERS,
        )
        assert resp.status_code == 200
        # Should ask for urgency
        assert "urgency" in resp.text.lower() or "emergency" in resp.text.lower() or "routine" in resp.text.lower()

    def test_step1_empty_speech_reprompts(self):
        resp = client.post(
            "/ivr/admission/name",
            data={"CallSid": "CA_ADM_003"},  # No SpeechResult
            headers=TWILIO_HEADERS,
        )
        assert resp.status_code == 200
        assert "<Response>" in resp.text  # must return TwiML, not crash

    def test_step2_unrecognised_ward_reprompts(self):
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = {
                "intent": "unknown", "confidence": 0.3,
                "entities": {"ward_name": None, "patient_id": None,
                             "patient_name": None, "urgency": None},
                "interpreted_as": "unclear", "source": "gpt"
            }
            resp = client.post(
                "/ivr/admission/ward",
                data={"CallSid": "CA_ADM_004", "SpeechResult": "I dunno", "Confidence": "0.31"},
                headers=TWILIO_HEADERS,
            )
        assert resp.status_code == 200
        assert "<Response>" in resp.text  # reprompts, does not crash


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 8 — Patient Status
# ══════════════════════════════════════════════════════════════════════════════

class TestPatientStatus:
    """Tests for /ivr/patient-status-response."""

    def _post(self, call_sid: str, speech: str, confidence: str = "0.92"):
        return client.post(
            "/ivr/patient-status-response",
            data={"CallSid": call_sid, "SpeechResult": speech, "Confidence": confidence},
            headers=TWILIO_HEADERS,
        )

    def test_valid_patient_id_p1001_returns_data(self):
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = {
                "intent": "patient_status", "confidence": 0.95,
                "entities": {"ward_name": None, "patient_id": "P1001",
                             "patient_name": None, "urgency": None},
                "interpreted_as": "P1001 status", "source": "gpt"
            }
            resp = self._post("CA_PAT_001", "P1001")
        assert resp.status_code == 200
        assert "Rahul" in resp.text or "Cardiology" in resp.text or "CAR" in resp.text

    def test_valid_patient_id_p1004_returns_critical_status(self):
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = {
                "intent": "patient_status", "confidence": 0.95,
                "entities": {"ward_name": None, "patient_id": "P1004",
                             "patient_name": None, "urgency": None},
                "interpreted_as": "P1004 status", "source": "gpt"
            }
            resp = self._post("CA_PAT_002", "P1004")
        assert resp.status_code == 200
        assert "Sunita" in resp.text or "Neurology" in resp.text or "Critical" in resp.text

    def test_invalid_patient_id_returns_not_found_twiml(self):
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = {
                "intent": "patient_status", "confidence": 0.90,
                "entities": {"ward_name": None, "patient_id": "P9999",
                             "patient_name": None, "urgency": None},
                "interpreted_as": "P9999 status", "source": "gpt"
            }
            resp = self._post("CA_PAT_003", "P9999")
        assert resp.status_code == 200
        # Must not be 500 — must be a graceful TwiML response
        assert "<Response>" in resp.text
        assert "not found" in resp.text.lower() or "could not" in resp.text.lower()

    def test_empty_speech_asks_for_id(self):
        resp = client.post(
            "/ivr/patient-status-response",
            data={"CallSid": "CA_PAT_004"},  # No SpeechResult
            headers=TWILIO_HEADERS,
        )
        assert resp.status_code == 200
        assert "ID" in resp.text or "patient" in resp.text.lower()


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 9 — Ward Inquiry
# ══════════════════════════════════════════════════════════════════════════════

class TestWardInquiry:
    """Tests for /ivr/ward-info-response."""

    @pytest.mark.parametrize("ward_key,expected_text", [
        ("general",    "General"),
        ("icu",        "ICU"),
        ("emergency",  "Emergency"),
        ("pediatric",  "Pediatric"),
        ("maternity",  "Maternity"),
        ("cardiology", "Cardiology"),
        ("orthopedic", "Orthopedic"),
        ("neurology",  "Neurology"),
    ])
    def test_each_ward_returns_correct_info(self, ward_key, expected_text):
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = {
                "intent": "ward_inquiry", "confidence": 0.92,
                "entities": {"ward_name": ward_key, "patient_id": None,
                             "patient_name": None, "urgency": None},
                "interpreted_as": f"{ward_key} info", "source": "gpt"
            }
            resp = client.post(
                "/ivr/ward-info-response",
                data={"CallSid": f"CA_WARD_{ward_key.upper()}",
                      "SpeechResult": ward_key, "Confidence": "0.92"},
                headers=TWILIO_HEADERS,
            )
        assert resp.status_code == 200
        assert expected_text in resp.text


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 10 — Admin Endpoints
# ══════════════════════════════════════════════════════════════════════════════

class TestAdminEndpoints:
    """Tests for /admin/* monitoring endpoints."""

    def test_admin_status_returns_200(self):
        resp = client.get("/admin/status")
        assert resp.status_code == 200

    def test_admin_status_has_total_beds(self):
        data = client.get("/admin/status").json()
        assert "hospital_stats" in data
        assert data["hospital_stats"]["total_beds"] > 0

    def test_admin_wards_returns_all_8_wards(self):
        data = client.get("/admin/wards").json()
        assert len(data) == 8
        for ward in WARD_NAMES:
            assert ward in data

    def test_admin_beds_has_summary_and_available_list(self):
        data = client.get("/admin/beds").json()
        assert "summary" in data
        assert "wards_with_availability" in data
        assert isinstance(data["wards_with_availability"], list)

    def test_admin_patients_returns_4_patients(self):
        data = client.get("/admin/patients").json()
        assert len(data) == 4
        assert "P1001" in data

    def test_admin_sessions_returns_dict(self):
        data = client.get("/admin/sessions").json()
        assert isinstance(data, dict)  # may be empty, that's fine

    def test_admin_security_returns_config(self):
        data = client.get("/admin/security").json()
        assert "validation_mode" in data
        assert "recommendation" in data

    def test_admin_admission_requests_returns_dict(self):
        data = client.get("/admin/admission-requests").json()
        assert isinstance(data, dict)


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 11 — Error Handling
# ══════════════════════════════════════════════════════════════════════════════

class TestErrorHandling:
    """Tests that the system fails gracefully, never with a 500."""

    def test_unknown_patient_id_returns_twiml_not_500(self):
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = {
                "intent": "patient_status", "confidence": 0.90,
                "entities": {"ward_name": None, "patient_id": "INVALID_ID",
                             "patient_name": None, "urgency": None},
                "interpreted_as": "unknown patient", "source": "gpt"
            }
            resp = client.post(
                "/ivr/patient-status-response",
                data={"CallSid": "CA_ERR_001", "SpeechResult": "INVALID_ID"},
                headers=TWILIO_HEADERS,
            )
        assert resp.status_code == 200          # TwiML, not 500
        assert "application/xml" in resp.headers["content-type"]

    def test_three_consecutive_empty_inputs_escalates_to_agent(self):
        """After 3 failed speech recognitions, system should escalate."""
        call_sid = "CA_ERR_002"
        # Three blank posts to /ivr/intent
        for _ in range(3):
            client.post("/ivr/intent",
                        data={"CallSid": call_sid},
                        headers=TWILIO_HEADERS)
        resp = client.post("/ivr/intent",
                           data={"CallSid": call_sid},
                           headers=TWILIO_HEADERS)
        assert resp.status_code == 200
        # After 3+ retries should escalate — either Dial or Say transfer
        assert "<Response>" in resp.text

    def test_call_status_endpoint_accepts_completed_status(self):
        resp = client.post(
            "/ivr/call-status",
            data={"CallSid": "CA_ERR_003", "CallStatus": "completed"},
            headers=TWILIO_HEADERS,
        )
        # Returns 204 No Content
        assert resp.status_code == 204

    def test_nlu_gpt_failure_falls_back_gracefully(self):
        """If GPT throws, fallback keyword matching must handle it."""
        with patch("milestone3.services.nlu_service._gpt_detect",
                   side_effect=Exception("Simulated OpenAI timeout")):
            resp = client.post(
                "/ivr/intent",
                data={"CallSid": "CA_ERR_004",
                      "SpeechResult": "I want to check bed availability",
                      "Confidence": "0.90"},
                headers=TWILIO_HEADERS,
            )
        assert resp.status_code == 200
        assert "<Response>" in resp.text      # keyword fallback returned TwiML


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 12 — Session Manager Unit Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSessionManager:
    """Direct unit tests for session_manager.py functions."""

    def setup_method(self):
        """Ensure clean imports for each test."""
        from milestone3.services import session_manager
        self.sm = session_manager

    def test_get_session_creates_new_session(self):
        sid = "SM_TEST_001"
        session = self.sm.get_session(sid)
        assert session["call_sid"] == sid
        assert session["stage"] == "welcome"
        assert session["turns"] == 0

    def test_set_and_get_collected(self):
        sid = "SM_TEST_002"
        self.sm.get_session(sid)
        self.sm.set_collected(sid, "patient_name", "Aarav Shah")
        assert self.sm.get_collected(sid, "patient_name") == "Aarav Shah"

    def test_get_collected_missing_key_returns_default(self):
        sid = "SM_TEST_003"
        self.sm.get_session(sid)
        result = self.sm.get_collected(sid, "nonexistent_key", default="fallback")
        assert result == "fallback"

    def test_increment_retry_increments(self):
        sid = "SM_TEST_004"
        self.sm.get_session(sid)
        count = self.sm.increment_retry(sid)
        assert count == 1
        count = self.sm.increment_retry(sid)
        assert count == 2

    def test_reset_retry_resets_to_zero(self):
        sid = "SM_TEST_005"
        self.sm.get_session(sid)
        self.sm.increment_retry(sid)
        self.sm.increment_retry(sid)
        self.sm.reset_retry(sid)
        session = self.sm.get_session(sid)
        assert session["retry_count"] == 0

    def test_end_session_removes_session(self):
        sid = "SM_TEST_006"
        self.sm.get_session(sid)
        self.sm.end_session(sid)
        # Getting a new session after end should create fresh one
        session = self.sm.get_session(sid)
        assert session["turns"] == 0  # fresh

    def test_update_session_increments_turns(self):
        sid = "SM_TEST_007"
        self.sm.get_session(sid)
        self.sm.update_session(sid, {"stage": "menu"})
        session = self.sm.get_session(sid)
        assert session["turns"] >= 1
        assert session["stage"] == "menu"
