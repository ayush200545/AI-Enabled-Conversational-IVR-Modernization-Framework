def create_twiml_say(message: str) -> str:
    """
    Generates TwiML to simply speak a message and hang up.
    """
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi" language="en-IN">{message}</Say>
    <Hangup/>
</Response>'''

def create_twiml_gather(message: str, action_url: str, timeout: int = 5) -> str:
    """
    Generates TwiML to speak a message and wait for speech or digit input.
    """
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech dtmf" timeout="{timeout}" action="{action_url}" method="POST" language="en-IN">
        <Say voice="Polly.Aditi" language="en-IN">{message}</Say>
    </Gather>
</Response>'''
