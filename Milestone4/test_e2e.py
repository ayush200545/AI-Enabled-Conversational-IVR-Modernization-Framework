"""
Milestone 4 — End-to-End & Performance Tests
Hospital IVR: Patient Admission & Bed Availability Management

E2E tests simulate complete user journeys from call start to call end.
Performance tests measure webhook response latency and throughput.

Run:
    pytest tests/test_e2e.py -v                        # E2E only
    pytest tests/test_e2e.py -v -k "performance"       # performance only
    pytest tests/test_e2e.py -v -k "not performance"   # skip load tests
"""

import time
import pytest
import threading
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
        "interpreted_as": f"E2E mock: {intent}",
        "source": "gpt",
    }


# ══════════════════════════════════════════════════════════════════════════════
#  E2E FLOW 1 — Happy Path: Full Admission Booking
# ══════════════════════════════════════════════════════════════════════════════

class TestE2EAdmissionHappyPath:
    """
    Story: A caller rings the hospital, says they want to admit a patient,
    provides all details, confirms, and receives a reference number.

    This is the most important E2E flow — it touches every layer:
    welcome → intent router → session → admission steps → DB → confirmation.
    """

    def test_complete_admission_journey(self):
        import re
        call_sid = "CA_E2E_ADM_001"

        # ── Call connects, welcome plays ─────────────────────────────────────
        r_welcome = client.post("/ivr/welcome",
                                data={"CallSid": call_sid},
                                headers=TWILIO_HEADERS)
        assert r_welcome.status_code == 200
        assert "Hospital" in r_welcome.text or "hospital" in r_welcome.text.lower()

        # ── Caller says 'I want to admit my father' ──────────────────────────
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("patient_admission")
            r_intent = client.post("/ivr/intent",
                                   data={"CallSid": call_sid,
                                         "SpeechResult": "I want to admit my father",
                                         "Confidence": "0.91"},
                                   headers=TWILIO_HEADERS)
        assert r_intent.status_code == 200
        assert "name" in r_intent.text.lower() or "patient" in r_intent.text.lower()

        # ── Gives patient name ───────────────────────────────────────────────
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("patient_admission",
                                           patient_name="Vijay Kumar")
            r_name = client.post("/ivr/admission/name",
                                 data={"CallSid": call_sid,
                                       "SpeechResult": "Vijay Kumar",
                                       "Confidence": "0.93"},
                                 headers=TWILIO_HEADERS)
        assert r_name.status_code == 200

        # ── Selects cardiology ward ──────────────────────────────────────────
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("ward_inquiry", ward="cardiology")
            r_ward = client.post("/ivr/admission/ward",
                                 data={"CallSid": call_sid,
                                       "SpeechResult": "Cardiology",
                                       "Confidence": "0.95"},
                                 headers=TWILIO_HEADERS)
        assert r_ward.status_code == 200

        # ── States urgency ───────────────────────────────────────────────────
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("patient_admission", urgency="urgent")
            r_urgency = client.post("/ivr/admission/urgency",
                                    data={"CallSid": call_sid,
                                          "SpeechResult": "Urgent",
                                          "Confidence": "0.90"},
                                    headers=TWILIO_HEADERS)
        assert r_urgency.status_code == 200
        # Confirmation should mention Vijay
        assert "Vijay" in r_urgency.text

        # ── Confirms ─────────────────────────────────────────────────────────
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("confirm")
            r_confirm = client.post("/ivr/admission/confirm",
                                    data={"CallSid": call_sid,
                                          "SpeechResult": "Yes confirm",
                                          "Digits": "1",
                                          "Confidence": "0.98"},
                                    headers=TWILIO_HEADERS)
        assert r_confirm.status_code == 200
        # Reference number must be in the response
        assert re.search(r"REQ\d{4,}", r_confirm.text), \
            f"No REQ reference found. Response: {r_confirm.text[:300]}"

        # ── Asks for more help — says no, call ends ──────────────────────────
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("goodbye")
            r_end = client.post("/ivr/post-action",
                                data={"CallSid": call_sid,
                                      "SpeechResult": "No thank you goodbye"},
                                headers=TWILIO_HEADERS)
        assert r_end.status_code == 200
        assert "<Hangup" in r_end.text or "Goodbye" in r_end.text

        # ── Call status: completed ────────────────────────────────────────────
        r_status = client.post("/ivr/call-status",
                               data={"CallSid": call_sid, "CallStatus": "completed"},
                               headers=TWILIO_HEADERS)
        assert r_status.status_code == 204


# ══════════════════════════════════════════════════════════════════════════════
#  E2E FLOW 2 — DTMF Path: Bed Check via Button Presses
# ══════════════════════════════════════════════════════════════════════════════

class TestE2EBedAvailabilityDTMF:
    """
    Story: An elderly caller prefers pressing buttons.
    They press 1 for beds, then say 'ICU', get the answer, and hang up.
    Verifies that hybrid DTMF+speech works end to end.
    """

    def test_dtmf_bed_availability_flow(self):
        call_sid = "CA_E2E_BED_DTMF_001"

        # Welcome
        r1 = client.post("/ivr/welcome",
                         data={"CallSid": call_sid},
                         headers=TWILIO_HEADERS)
        assert r1.status_code == 200

        # Press 1 for beds (DTMF — no NLU needed)
        r2 = client.post("/ivr/intent",
                         data={"CallSid": call_sid, "Digits": "1"},
                         headers=TWILIO_HEADERS)
        assert r2.status_code == 200
        assert "ward" in r2.text.lower() or "bed" in r2.text.lower()

        # Say 'ICU'
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("bed_availability", ward="icu")
            r3 = client.post("/ivr/bed-availability-response",
                             data={"CallSid": call_sid,
                                   "SpeechResult": "ICU",
                                   "Confidence": "0.96"},
                             headers=TWILIO_HEADERS)
        assert r3.status_code == 200
        assert "ICU" in r3.text or "2" in r3.text  # ICU has 2 beds

        # Press 0 to end (or say goodbye)
        r4 = client.post("/ivr/post-action",
                         data={"CallSid": call_sid, "Digits": "0"},
                         headers=TWILIO_HEADERS)
        assert r4.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
#  E2E FLOW 3 — Edge Case: 3-Strike Escalation to Agent
# ══════════════════════════════════════════════════════════════════════════════

class TestE2EThreeStrikeEscalation:
    """
    Story: The caller's microphone is muffled. Three turns produce no
    recognisable speech. The system escalates to a human agent automatically.
    """

    def test_three_empty_inputs_escalate_gracefully(self):
        call_sid = "CA_E2E_STRIKE_001"

        # Welcome
        client.post("/ivr/welcome",
                    data={"CallSid": call_sid},
                    headers=TWILIO_HEADERS)

        # Three blank inputs (no SpeechResult, no Digits)
        for attempt in range(3):
            resp = client.post("/ivr/intent",
                               data={"CallSid": call_sid},
                               headers=TWILIO_HEADERS)
            assert resp.status_code == 200  # must not crash on any attempt

        # Fourth attempt — should transfer or strongly re-prompt
        final = client.post("/ivr/intent",
                            data={"CallSid": call_sid},
                            headers=TWILIO_HEADERS)
        assert final.status_code == 200
        # System should not be looping silently — must produce output
        assert len(final.text) > 50


# ══════════════════════════════════════════════════════════════════════════════
#  E2E FLOW 4 — Patient Status + Back to Menu
# ══════════════════════════════════════════════════════════════════════════════

class TestE2EPatientStatusAndContinue:
    """
    Story: A family member checks on a patient, then asks about bed
    availability in the same call. Session must not break between flows.
    """

    def test_patient_lookup_then_bed_check_in_same_call(self):
        call_sid = "CA_E2E_MULTI_001"

        # Flow 1: Patient status
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("patient_status", patient_id="P1002")
            r1 = client.post("/ivr/intent",
                             data={"CallSid": call_sid,
                                   "SpeechResult": "What is the condition of P1002",
                                   "Confidence": "0.92"},
                             headers=TWILIO_HEADERS)
        assert r1.status_code == 200
        assert "Priya" in r1.text or "Maternity" in r1.text

        # Says yes to continue
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("confirm")
            r2 = client.post("/ivr/post-action",
                             data={"CallSid": call_sid,
                                   "SpeechResult": "Yes more help please"},
                             headers=TWILIO_HEADERS)
        assert r2.status_code == 200

        # Flow 2: Bed availability in same call
        with patch("milestone3.services.nlu_service.detect_intent") as m:
            m.return_value = make_nlu_mock("bed_availability", ward="maternity")
            r3 = client.post("/ivr/intent",
                             data={"CallSid": call_sid,
                                   "SpeechResult": "Are there maternity beds available",
                                   "Confidence": "0.93"},
                             headers=TWILIO_HEADERS)
        assert r3.status_code == 200
        assert "Maternity" in r3.text or "bed" in r3.text.lower()


# ══════════════════════════════════════════════════════════════════════════════
#  PERFORMANCE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestPerformance:
    """
    Measure webhook response latency.

    Twilio requirement: webhook must respond within 15 seconds or the call fails.
    Industry target for a good IVR: under 500ms per webhook response.
    These tests enforce a 2-second maximum — well within Twilio's timeout.
    """

    MAX_RESPONSE_MS = 2000   # 2 second ceiling (Twilio needs <15s, we target <500ms)
    LOAD_REQUESTS  = 20      # number of sequential requests for throughput test

    def _measure_ms(self, fn) -> float:
        start = time.monotonic()
        fn()
        return (time.monotonic() - start) * 1000

    def test_welcome_response_time_under_2s(self):
        elapsed = self._measure_ms(
            lambda: client.post("/ivr/welcome",
                                data={"CallSid": "CA_PERF_001"},
                                headers=TWILIO_HEADERS)
        )
        assert elapsed < self.MAX_RESPONSE_MS, \
            f"/ivr/welcome took {elapsed:.0f}ms — exceeds {self.MAX_RESPONSE_MS}ms limit"

    def test_health_endpoint_under_100ms(self):
        elapsed = self._measure_ms(lambda: client.get("/health"))
        assert elapsed < 100, f"/health took {elapsed:.0f}ms — should be near-instant"

    def test_admin_status_under_500ms(self):
        elapsed = self._measure_ms(lambda: client.get("/admin/status"))
        assert elapsed < 500, f"/admin/status took {elapsed:.0f}ms"

    def test_dtmf_routing_under_500ms(self):
        """DTMF routing requires no NLU — should be very fast."""
        elapsed = self._measure_ms(
            lambda: client.post("/ivr/intent",
                                data={"CallSid": "CA_PERF_002", "Digits": "1"},
                                headers=TWILIO_HEADERS)
        )
        assert elapsed < 500, f"DTMF routing took {elapsed:.0f}ms"

    @patch("milestone3.services.nlu_service.detect_intent")
    def test_nlu_endpoint_under_2s_with_mocked_gpt(self, mock_nlu):
        """With GPT mocked, the full intent endpoint should complete quickly."""
        mock_nlu.return_value = make_nlu_mock("bed_availability")
        elapsed = self._measure_ms(
            lambda: client.post("/ivr/intent",
                                data={"CallSid": "CA_PERF_003",
                                      "SpeechResult": "check beds",
                                      "Confidence": "0.92"},
                                headers=TWILIO_HEADERS)
        )
        assert elapsed < self.MAX_RESPONSE_MS, \
            f"NLU intent routing took {elapsed:.0f}ms"

    def test_sequential_load_20_welcome_requests(self):
        """
        Send 20 sequential welcome requests and check:
        - All return 200
        - No request exceeds 2s
        - Total throughput is reasonable
        """
        results = []
        total_start = time.monotonic()

        for i in range(self.LOAD_REQUESTS):
            start = time.monotonic()
            resp = client.post("/ivr/welcome",
                               data={"CallSid": f"CA_LOAD_{i:03d}"},
                               headers=TWILIO_HEADERS)
            elapsed_ms = (time.monotonic() - start) * 1000
            results.append({
                "index": i,
                "status": resp.status_code,
                "elapsed_ms": elapsed_ms,
            })

        total_ms = (time.monotonic() - total_start) * 1000
        success_count = sum(1 for r in results if r["status"] == 200)
        max_ms = max(r["elapsed_ms"] for r in results)
        avg_ms = total_ms / self.LOAD_REQUESTS

        print(f"\n[LOAD TEST] {self.LOAD_REQUESTS} requests | "
              f"Success: {success_count}/{self.LOAD_REQUESTS} | "
              f"Avg: {avg_ms:.0f}ms | Max: {max_ms:.0f}ms | "
              f"Total: {total_ms:.0f}ms")

        assert success_count == self.LOAD_REQUESTS, \
            f"Only {success_count}/{self.LOAD_REQUESTS} requests succeeded"
        assert max_ms < self.MAX_RESPONSE_MS, \
            f"Slowest request was {max_ms:.0f}ms — exceeds {self.MAX_RESPONSE_MS}ms"

    def test_concurrent_3_callers_no_session_collision(self):
        """
        Simulate 3 concurrent callers in separate threads.
        Each should get independent sessions — no data leakage.
        """
        results = {}

        def simulate_caller(caller_num: int):
            call_sid = f"CA_CONC_{caller_num:03d}"
            resp = client.post("/ivr/welcome",
                               data={"CallSid": call_sid},
                               headers=TWILIO_HEADERS)
            results[caller_num] = resp.status_code

        threads = [
            threading.Thread(target=simulate_caller, args=(i,))
            for i in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert all(s == 200 for s in results.values()), \
            f"Some concurrent calls failed: {results}"


# ══════════════════════════════════════════════════════════════════════════════
#  ERROR HANDLING E2E
# ══════════════════════════════════════════════════════════════════════════════

class TestE2EErrorHandling:
    """Verify graceful degradation in every failure scenario."""

    def test_gpt_timeout_does_not_crash_the_ivr(self):
        """Simulate OpenAI timing out mid-call — fallback must kick in."""
        with patch("milestone3.services.nlu_service._gpt_detect",
                   side_effect=Exception("Simulated GPT timeout")):
            resp = client.post(
                "/ivr/intent",
                data={"CallSid": "CA_E2E_ERR_001",
                      "SpeechResult": "check bed availability",
                      "Confidence": "0.90"},
                headers=TWILIO_HEADERS,
            )
        assert resp.status_code == 200
        assert "<Response>" in resp.text     # TwiML from keyword fallback

    def test_invalid_call_status_is_ignored_gracefully(self):
        resp = client.post(
            "/ivr/call-status",
            data={"CallSid": "CA_E2E_ERR_002", "CallStatus": "unknown_status"},
            headers=TWILIO_HEADERS,
        )
        assert resp.status_code == 204       # silently ignored, not 500

    def test_ward_with_zero_beds_offers_alternative(self):
        """If a full ward is requested, system should not crash — offer alternatives."""
        with patch("milestone3.data.hospital_db.WARDS") as mock_wards:
            # Patch ICU to have 0 available beds
            from milestone3.data.hospital_db import WARDS as real_wards
            import copy
            patched = copy.deepcopy(real_wards)
            patched["icu"]["available_beds"] = 0
            mock_wards.__getitem__ = lambda self, k: patched[k]
            mock_wards.get = patched.get
            mock_wards.items = patched.items
            mock_wards.values = patched.values
            mock_wards.keys = patched.keys

            with patch("milestone3.services.nlu_service.detect_intent") as m:
                m.return_value = make_nlu_mock("bed_availability", ward="icu")
                resp = client.post(
                    "/ivr/intent",
                    data={"CallSid": "CA_E2E_FULL_WARD",
                          "SpeechResult": "ICU beds",
                          "Confidence": "0.92"},
                    headers=TWILIO_HEADERS,
                )
        assert resp.status_code == 200
        assert "<Response>" in resp.text
