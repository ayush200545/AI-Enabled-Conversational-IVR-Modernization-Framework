import random

# A mock session cache to simulate state across the call
# In production, this would be Redis or a database.
session_cache = {}

def process_conversational_intent(session_id: str, text_input: str) -> str:
    """
    Simulates the integration layer between the legacy IVR / Twilio and 
    a Conversational AI platform (like ACS or BAP Services).
    
    In a real-world scenario, this function would build an API request 
    to the LLM endpoint (e.g. OpenAI, Azure), appending dialogue history
    stored by session_id.
    """
    text_lower = text_input.lower()
    
    # Initialize session state if not exists
    if session_id not in session_cache:
        session_cache[session_id] = {"interactions": 0}
        
    session_cache[session_id]["interactions"] += 1
    
    # Mock NLU / Intent Recognition Logic
    if "book" in text_lower or "flight" in text_lower or "ticket" in text_lower:
        return "I understand you want to book a ticket. Where will you be traveling to?"
        
    elif "balance" in text_lower or "account" in text_lower:
        return "Your current account balance is mock $1,250. Is there anything else you need?"
        
    elif "agent" in text_lower or "human" in text_lower:
        return "Transferring you to a human agent now. Please wait."
        
    elif "thank" in text_lower or "bye" in text_lower:
        return "Thank you for calling. Goodbye!"
        
    else:
        # Fallback response
        return "I'm processing your request regarding: '" + text_input + "'. Can you provide more details?"
