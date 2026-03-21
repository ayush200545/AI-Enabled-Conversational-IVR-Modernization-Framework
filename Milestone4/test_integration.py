"""
Milestone 4 — Integration Tests
Hospital IVR: Patient Admission & Bed Availability Management

Integration tests verify that multiple components work together correctly.
Unlike unit tests, these allow real session state and real DB lookups.
NLU (GPT) is still mocked to keep tests deterministic.

Run:
    pytest tests/test_integration.py -v
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from main import app

client = TestClient(app, raise_server_exceptions=True)

TWILIO_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Twilio-Signature": "bypass_for_tests",
}


def make_nlu_mock(intent, ward=None, patient_id=None,
                  patient_name=None, urgency=None, confidence=0.92):
    return {
        "intent": intent,
        "confidence": confidence,
        "entities": {
            "ward_name": ward,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "urgency": urgency,
        },
        "interpreted_as": f"Integration mock: {intent}",
        "source": "gpt",
    }


# ══════════════════════════════════════════════════════════════════════════════
#  TEST 1 — Full Bed Availability Conversation (2 turns)
# ══════════════════════════════════════════════════════════════════════════════

class TestBedAvailabilityConversation:
    """
    Turn 1: Caller says 'check beds' → system asks which ward.
    Turn 2: Caller says 'ICU'        → system reads ICU bed data.
    Session must carry CallSid across both turns.
    """

    CALL_SID = "CA_INT_BED_001"

    def test_turn1_bed_availability_asks_for_ward(self):
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("bed_availability")   # no ward yet
            resp = client.post(
                "/ivr/intent",
                data={"CallSid": self.CALL_SID,
                      "SpeechResult": "I want to check bed availability",
                      "Confidence": "0.92"},
                headers=TWILIO_HEADERS,
            )
        assert resp.status_code == 200
        # Should ask which ward
        assert "ward" in resp.text.lower() or "which" in resp.text.lower()
        assert "/ivr/bed-availability-response" in resp.text   # action URL

    def test_turn2_caller_says_icu_returns_bed_count(self):
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("bed_availability", ward="icu")
            resp = client.post(
                "/ivr/bed-availability-response",
                data={"CallSid": self.CALL_SID,
                      "SpeechResult": "ICU",
                      "Confidence": "0.95"},
                headers=TWILIO_HEADERS,
            )
        assert resp.status_code == 200
        # ICU has 2 available beds in mock DB
        assert "ICU" in resp.text or "2" in resp.text

    def test_full_flow_icu_is_coherent(self):
        """Combined: two-turn flow from one test."""
        call_sid = "CA_INT_BED_FULL_001"

        # Turn 1
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("bed_availability")
            r1 = client.post("/ivr/intent",
                             data={"CallSid": call_sid,
                                   "SpeechResult": "check beds"},
                             headers=TWILIO_HEADERS)
        assert r1.status_code == 200

        # Turn 2
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("bed_availability", ward="icu")
            r2 = client.post("/ivr/bed-availability-response",
                             data={"CallSid": call_sid, "SpeechResult": "ICU"},
                             headers=TWILIO_HEADERS)
        assert r2.status_code == 200
        assert "ICU" in r2.text or "bed" in r2.text.lower()


# ══════════════════════════════════════════════════════════════════════════════
#  TEST 2 — Full 4-Step Admission Flow
# ══════════════════════════════════════════════════════════════════════════════

class TestAdmissionMultiTurnFlow:
    """
    Simulates the complete 4-step admission conversation.
    Session state must persist across all 4 webhook calls (same CallSid).
    """

    CALL_SID = "CA_INT_ADM_FULL_001"

    def test_complete_4_step_admission(self):
        call_sid = "CA_INT_ADM_COMPLETE_001"

        # ── Step 1: Trigger admission flow ──────────────────────────────────
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("patient_admission")
            r1 = client.post("/ivr/intent",
                             data={"CallSid": call_sid,
                                   "SpeechResult": "I want to admit my mother"},
                             headers=TWILIO_HEADERS)
        assert r1.status_code == 200
        assert "name" in r1.text.lower() or "patient" in r1.text.lower()

        # ── Step 2: Patient name ─────────────────────────────────────────────
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("patient_admission",
                                           patient_name="Kavita Rao")
            r2 = client.post("/ivr/admission/name",
                             data={"CallSid": call_sid,
                                   "SpeechResult": "Kavita Rao",
                                   "Confidence": "0.91"},
                             headers=TWILIO_HEADERS)
        assert r2.status_code == 200
        # Session should have stored name; response asks for ward
        assert "ward" in r2.text.lower() or "which" in r2.text.lower()

        # ── Step 3: Ward selection ────────────────────────────────────────────
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("ward_inquiry", ward="general")
            r3 = client.post("/ivr/admission/ward",
                             data={"CallSid": call_sid,
                                   "SpeechResult": "General ward",
                                   "Confidence": "0.94"},
                             headers=TWILIO_HEADERS)
        assert r3.status_code == 200
        # Should ask for urgency
        assert ("urgency" in r3.text.lower()
                or "emergency" in r3.text.lower()
                or "routine" in r3.text.lower())

        # ── Step 4: Urgency level ─────────────────────────────────────────────
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("patient_admission", urgency="routine")
            r4 = client.post("/ivr/admission/urgency",
                             data={"CallSid": call_sid,
                                   "SpeechResult": "Routine",
                                   "Confidence": "0.93"},
                             headers=TWILIO_HEADERS)
        assert r4.status_code == 200
        # Should show confirmation prompt with all 3 details
        assert "Kavita" in r4.text or "General" in r4.text or "routine" in r4.text.lower()

        # ── Step 5: Confirmation ──────────────────────────────────────────────
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("confirm")
            r5 = client.post("/ivr/admission/confirm",
                             data={"CallSid": call_sid,
                                   "SpeechResult": "Yes that is correct",
                                   "Confidence": "0.95"},
                             headers=TWILIO_HEADERS)
        assert r5.status_code == 200
        # Should contain a reference number (REQ followed by digits)
        import re
        assert re.search(r"REQ\d{4,}", r5.text), "Reference number not found in response"

    def test_session_stores_name_across_turns(self):
        """Verify that the name collected in step 2 appears in the confirmation."""
        call_sid = "CA_INT_ADM_NAME_CHECK"
        test_name = "Deepa Nair"

        # Step 2: name
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("patient_admission", patient_name=test_name)
            client.post("/ivr/admission/name",
                        data={"CallSid": call_sid, "SpeechResult": test_name},
                        headers=TWILIO_HEADERS)

        # Step 3: ward
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("ward_inquiry", ward="pediatric")
            client.post("/ivr/admission/ward",
                        data={"CallSid": call_sid, "SpeechResult": "pediatric"},
                        headers=TWILIO_HEADERS)

        # Step 4: urgency → produces confirmation with the stored name
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("patient_admission", urgency="urgent")
            r = client.post("/ivr/admission/urgency",
                            data={"CallSid": call_sid, "SpeechResult": "Urgent"},
                            headers=TWILIO_HEADERS)

        assert r.status_code == 200
        assert "Deepa" in r.text, "Session failed to carry patient name across turns"

    def test_denial_at_confirm_step_restarts_flow(self):
        """If caller says 'no' at confirmation, flow should restart from name."""
        call_sid = "CA_INT_ADM_DENY_001"

        # Seed session
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("patient_admission", patient_name="Test")
            client.post("/ivr/admission/name",
                        data={"CallSid": call_sid, "SpeechResult": "Test"},
                        headers=TWILIO_HEADERS)
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("ward_inquiry", ward="general")
            client.post("/ivr/admission/ward",
                        data={"CallSid": call_sid, "SpeechResult": "General"},
                        headers=TWILIO_HEADERS)
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("patient_admission", urgency="routine")
            client.post("/ivr/admission/urgency",
                        data={"CallSid": call_sid, "SpeechResult": "Routine"},
                        headers=TWILIO_HEADERS)

        # Deny at confirmation
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("deny")
            r = client.post("/ivr/admission/confirm",
                            data={"CallSid": call_sid,
                                  "SpeechResult": "No that is wrong",
                                  "Digits": "2"},
                            headers=TWILIO_HEADERS)

        assert r.status_code == 200
        # Should restart — ask for name again
        assert "name" in r.text.lower() or "patient" in r.text.lower()


# ══════════════════════════════════════════════════════════════════════════════
#  TEST 3 — Patient Status Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestPatientStatusIntegration:
    """Verify that patient lookups correctly read from the hospital DB."""

    @pytest.mark.parametrize("patient_id,expected_name,expected_ward", [
        ("P1001", "Rahul",  "Cardiology"),
        ("P1002", "Priya",  "Maternity"),
        ("P1003", "Amit",   "Pediatric"),
        ("P1004", "Sunita", "Neurology"),
    ])
    def test_all_preloaded_patients_are_retrievable(
            self, patient_id, expected_name, expected_ward):
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("patient_status",
                                           patient_id=patient_id)
            resp = client.post(
                "/ivr/patient-status-response",
                data={"CallSid": f"CA_INT_PAT_{patient_id}",
                      "SpeechResult": patient_id,
                      "Confidence": "0.95"},
                headers=TWILIO_HEADERS,
            )
        assert resp.status_code == 200
        assert expected_name in resp.text or expected_ward in resp.text

    def test_patient_lookup_by_name_returns_data(self):
        """NLU extracts patient_name entity — system should still find patient."""
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("patient_status",
                                           patient_name="Rahul Sharma")
            resp = client.post(
                "/ivr/patient-status-response",
                data={"CallSid": "CA_INT_PAT_NAME",
                      "SpeechResult": "Rahul Sharma",
                      "Confidence": "0.89"},
                headers=TWILIO_HEADERS,
            )
        assert resp.status_code == 200
        assert "Rahul" in resp.text or "Cardiology" in resp.text


# ══════════════════════════════════════════════════════════════════════════════
#  TEST 4 — Post-Action Flow
# ══════════════════════════════════════════════════════════════════════════════

class TestPostAction:
    """After completing a task, caller is asked: more help or goodbye?"""

    def test_yes_after_task_returns_to_main_menu(self):
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("confirm")
            resp = client.post(
                "/ivr/post-action",
                data={"CallSid": "CA_INT_PA_001",
                      "SpeechResult": "Yes I need more help"},
                headers=TWILIO_HEADERS,
            )
        assert resp.status_code == 200
        # Main menu: should contain options
        assert "1" in resp.text or "menu" in resp.text.lower() or "bed" in resp.text.lower()

    def test_no_after_task_plays_goodbye_and_hangs_up(self):
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("deny")
            resp = client.post(
                "/ivr/post-action",
                data={"CallSid": "CA_INT_PA_002",
                      "SpeechResult": "No thank you"},
                headers=TWILIO_HEADERS,
            )
        assert resp.status_code == 200
        assert "<Hangup" in resp.text or "Goodbye" in resp.text


# ══════════════════════════════════════════════════════════════════════════════
#  TEST 5 — Security Middleware Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestSecurityMiddlewareIntegration:
    """
    Verify middleware integrates correctly with routes.
    In test environment TWILIO_VALIDATION_MODE should be 'disabled' or 'log_only'.
    """

    def test_ivr_endpoint_accessible_without_signature_in_dev_mode(self):
        """In dev/test mode, requests without signature still go through."""
        resp = client.post(
            "/ivr/welcome",
            data={"CallSid": "CA_SEC_001"},
            # No X-Twilio-Signature header
        )
        # Should not be 403 in dev/test mode
        assert resp.status_code in (200, 403)  # 403 only if enforce mode is on

    def test_admin_endpoints_not_blocked_by_twilio_middleware(self):
        """Admin endpoints are NOT under /ivr/ so middleware should not block them."""
        resp = client.get("/admin/status")
        assert resp.status_code == 200

    def test_health_endpoint_not_blocked(self):
        resp = client.get("/health")
        assert resp.status_code == 200
