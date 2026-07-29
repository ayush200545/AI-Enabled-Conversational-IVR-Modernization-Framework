import pytest
from fastapi.testclient import TestClient
from app.main import app

# Initialize the TestClient with the app instance (Fixed intentional bug from Module 4)
client = TestClient(app)

# ---------------------------------------------------------
# 1. UNIT TESTS (Fast, isolated tests)
# ---------------------------------------------------------
def test_root():
    """Verify the root endpoint returns 200 and expected message."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Welcome" in resp.json().get("message", "")

def test_ivr_welcome():
    """Verify the Twilio welcome webhook returns valid TwiML."""
    # Twilio sends POST requests
    resp = client.post("/ivr/welcome")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/xml"
    
    xml_content = resp.text
    assert "<Response>" in xml_content
    assert "<Gather" in xml_content
    assert "Welcome to the AI Enabled IVR System" in xml_content


# ---------------------------------------------------------
# 2. INTEGRATION TESTS (Testing API layers talking to logic)
# ---------------------------------------------------------
def test_conversation_flow_fallback():
    """Verify the backend handles empty input and falls back correctly."""
    resp = client.post(
        "/ivr/handle-input",
        data={
            "CallSid": "test_call_001",
            "From": "+1234567890",
            "SpeechResult": "",  # Empty speech
            "Digits": ""
        }
    )
    assert resp.status_code == 200
    assert "I'm sorry, I didn't catch that" in resp.text


# ---------------------------------------------------------
# 3. END-TO-END (E2E) TESTS (Simulating full user journey)
# ---------------------------------------------------------
def test_full_ivr_flow():
    """Simulate a caller completing a booking flow using the Twilio Track approach."""
    call_id = "ivr_user_002"
    
    # Step 1: Start the IVR session
    start = client.post("/ivr/welcome")
    assert start.status_code == 200
    assert "Welcome" in start.text
    
    # Step 2: Simulate user speaking "Book a flight"
    handle = client.post(
        "/ivr/handle-input",
        data={  # Fixed typo: 'paramas' to 'data' (Form data for Twilio)
            "CallSid": call_id,
            "From": "+19999999999",
            "SpeechResult": "Book a flight"
        }
    )
    assert handle.status_code == 200
    assert "Where will you be traveling to?" in handle.text

    # Step 3: Simulate user speaking "Delhi"
    # The ai_integration layer currently returns a fallback for "delhi" since it's a mock
    dom = client.post(
        "/ivr/handle-input",
        data={
            "CallSid": call_id,
            "From": "+19999999999",
            "SpeechResult": "Delhi"
        }
    )
    assert dom.status_code == 200
    assert "processing your request regarding: 'Delhi'" in dom.text
    print("E2E flow completed successfully")


# ---------------------------------------------------------
# 4. ERROR HANDLING & LOGGING TESTS
# ---------------------------------------------------------
def test_invalid_endpoint():
    """Verify that hitting a non-existent endpoint returns 404 cleanly."""
    response = client.get("/flight/INVALID_ID")
    assert response.status_code == 404
    # FastAPI returns {"detail": "Not Found"} by default for unhandled 404s
    assert response.json()["detail"] == "Not Found"

def test_missing_form_data():
    """Verify that missing required form data returns 422 Unprocessable Entity."""
    # /ivr/handle-input requires CallSid and From
    response = client.post("/ivr/handle-input", data={})
    assert response.status_code == 422
