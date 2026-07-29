from fastapi import FastAPI
from app.api import twilio_webhook

app = FastAPI(
    title="Conversational IVR Modernization Framework",
    description="Middleware for Twilio to Conversational AI Integration",
    version="1.0.0"
)

app.include_router(twilio_webhook.router, prefix="/ivr", tags=["Twilio IVR"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Conversational IVR Modernization API. Use /ivr endpoints for Twilio Webhooks."}
