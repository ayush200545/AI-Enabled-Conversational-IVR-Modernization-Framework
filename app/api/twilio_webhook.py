from fastapi import APIRouter, Form, Request, Response
from app.utils.twiml_generator import create_twiml_gather, create_twiml_say
from app.services.ai_integration import process_conversational_intent

router = APIRouter()

@router.post("/welcome")
async def ivr_welcome():
    """
    Entry point for the Twilio Voice call.
    Greets the user and prompts them to speak their requirement.
    """
    message = "Welcome to the AI Enabled IVR System. How can I help you today? You can say things like 'Book a flight' or 'Check my balance'."
    twiml = create_twiml_gather(message, action_url="/ivr/handle-input")
    return Response(content=twiml, media_type="application/xml")

@router.post("/handle-input")
async def handle_input(
    CallSid: str = Form(...),
    From: str = Form(...),
    SpeechResult: str = Form(None),
    Digits: str = Form(None)
):
    """
    Receives transcribed speech (SpeechResult) or DTMF input (Digits) from Twilio.
    Passes the input to the AI layer and returns the intelligent response.
    """
    # Prefer speech input over digits if available
    user_input = SpeechResult or Digits

    if not user_input:
        # Fallback if no input received
        message = "I'm sorry, I didn't catch that. Please tell me how I can help you."
        twiml = create_twiml_gather(message, action_url="/ivr/handle-input")
        return Response(content=twiml, media_type="application/xml")

    # Send the transcribed text to the Conversational AI integration layer
    ai_response_text = process_conversational_intent(session_id=CallSid, text_input=user_input)

    # Convert the AI response back into TwiML
    twiml = create_twiml_gather(ai_response_text, action_url="/ivr/handle-input")
    return Response(content=twiml, media_type="application/xml")
