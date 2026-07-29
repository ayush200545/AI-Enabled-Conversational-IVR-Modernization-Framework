# Milestone 1: Legacy System Analysis and Requirements Gathering

## 1. Project Objective
To modernize existing IVR (Interactive Voice Response) systems built on VoiceXML (VXML) by integrating them with modern Conversational AI platforms such as ACS and BAP Service. By reusing and extending legacy assets, the solution will enable these systems to support conversational interfaces while minimizing rework. 

## 2. Review of Existing VXML Systems
Current IVR implementations operate on legacy VoiceXML (VXML) technology, which offers rule-based, rigid menu structures (e.g., "Press 1 for Sales, Press 2 for Support"). 
**Limitations:**
- Lack of Natural Language Understanding (NLU).
- Poor user experience due to deep, frustrating menu trees.
- Hardcoded dialogue states making updates and maintenance difficult.
- Inability to dynamically pull conversational context.

## 3. Integration Strategy
The goal is to move from DTMF (Dual-Tone Multi-Frequency) dependent flows to natural, speech-driven conversational flows. We will use a Middleware Integration Layer built in Python (FastAPI).

**Architecture:**
- **Voice Gateway**: Twilio Programmable Voice will replace or sit on top of the VXML layer, acting as the bridge to the user.
- **Middleware API**: A FastAPI service that processes Twilio webhooks (`/ivr/welcome`, `/ivr/handle-input`).
- **Conversational AI Engine**: The middleware will communicate with AI platforms (simulating ACS/BAP integration) to parse intent from user voice inputs (transcribed by Twilio) and generate intelligent text responses.
- **TwiML Generation**: The FastAPI service will return TwiML `<Response>` blocks utilizing `<Say>` (Text-to-Speech) and `<Gather>` (Speech Recognition) to interact with the caller.

## 4. Technical Integration Requirements
- **Webhooks**: RESTful POST endpoints capable of receiving Twilio payloads (CallSid, From, Digits, SpeechResult).
- **Latency**: Real-time data handling requires response times under 2000ms to avoid awkward silences on the call.
- **State Management**: The API must track conversation state across multiple webhook requests (e.g., using CallSid as a session key).
- **TTS/STT Integration**: Leverage Twilio's native Speech-to-Text and Text-to-Speech capabilities, sending only the transcribed text payload to the NLP AI engine.

## 5. Compatibility Gaps & Challenges
- **State Persistence**: Legacy VXML handles state locally within the script. The new API needs an external cache (like Redis) or robust in-memory handling for session states.
- **Speech Recognition Accuracy**: Background noise or accents may affect Twilio's `SpeechResult`. The AI layer must gracefully handle fallback or unrecognized intent scenarios.
- **Integration Layer Security**: The Webhook endpoints must be secured to only accept authenticated requests from Twilio to prevent abuse.
