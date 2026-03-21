"""
conftest.py — Shared pytest fixtures for Milestone 4 tests.

Fixtures defined here are available in all test files automatically.
"""

import os
import pytest

# ── Force test-safe environment before any imports ──────────────────────────
os.environ.setdefault("TWILIO_VALIDATION_MODE", "disabled")  # skip sig checks
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-not-real")  # NLU mocked


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Session-scoped: sets environment once for the whole test run."""
    os.environ["TWILIO_VALIDATION_MODE"] = "disabled"
    os.environ["OPENAI_API_KEY"] = "sk-test-key-not-real"
    yield


@pytest.fixture(autouse=True)
def clean_session_state():
    """
    Function-scoped: clears all active IVR sessions before each test.
    Prevents session state from leaking between tests.
    """
    from milestone3.services.session_manager import _sessions
    _sessions.clear()
    yield
    _sessions.clear()


@pytest.fixture
def test_call_sid():
    """Returns a unique CallSid per test."""
    import uuid
    return f"CA_FIXTURE_{uuid.uuid4().hex[:8].upper()}"


@pytest.fixture
def twilio_headers():
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Twilio-Signature": "bypass_for_tests",
    }


@pytest.fixture
def app_client():
    """FastAPI TestClient configured for testing."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def mock_nlu_bed_icu():
    """Pre-built NLU mock: bed_availability for ICU."""
    return {
        "intent": "bed_availability",
        "confidence": 0.95,
        "entities": {
            "ward_name": "icu",
            "patient_id": None,
            "patient_name": None,
            "urgency": None,
        },
        "interpreted_as": "Checking ICU bed availability",
        "source": "gpt",
    }


@pytest.fixture
def mock_nlu_patient_p1001():
    """Pre-built NLU mock: patient_status for P1001."""
    return {
        "intent": "patient_status",
        "confidence": 0.95,
        "entities": {
            "ward_name": None,
            "patient_id": "P1001",
            "patient_name": None,
            "urgency": None,
        },
        "interpreted_as": "Status of patient P1001",
        "source": "gpt",
    }
