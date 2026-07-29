# Conversational IVR Modernization Framework

## Project Overview
This project aims to modernize existing IVR (Interactive Voice Response) systems built on VoiceXML (VXML) by integrating them with modern Conversational AI platforms. By reusing and extending legacy assets, the solution enables these systems to support natural, conversational interfaces while minimizing redevelopment rework. 

The architecture bridges Twilio's programmable voice (acting as the IVR endpoint) with a scalable FastAPI backend, which handles real-time conversational context and routing, simulating integrations with advanced conversational models (like ACS or BAP Services).

## Key Features
- **VXML to AI Integration Layer**: Middleware built in FastAPI connecting Twilio voice Webhooks to Conversational AI logic.
- **Dynamic TwiML Generation**: Real-time generation of Twilio Markup Language to handle caller input, voice synthesis (TTS), and intelligent routing.
- **Mock AI Service**: A modular AI service layer ready for drop-in LLM/NLU API credentials, currently returning intelligent simulated responses for testing and demonstration purposes.
- **Production Ready Documentation**: Includes Agile sprint trackers, unit test plans, defect tracking, and legacy analysis documentation.

## Repository Structure
```
├── app/
│   ├── api/                # FastAPI routers for Twilio Webhooks
│   ├── services/           # Business logic and AI integration layer
│   ├── utils/              # TwiML generation and helper utilities
│   └── main.py             # FastAPI application entry point
├── docs/                   # Milestone documentation and project trackers
├── tests/                  # Unit testing files
├── .env.example            # Environment variables template
├── requirements.txt        # Python dependencies
├── LICENSE                 # MIT License
└── README.md               # Project documentation
```

## Setup Instructions

### 1. Prerequisites
- Python 3.9+
- A Twilio Account (for the phone number and webhook testing)
- `ngrok` (to expose your local server to Twilio)

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone <your-repo-link>
cd conversational-ivr-framework
python -m venv venv
# Windows: venv\Scripts\activate | Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env` and fill in your Twilio details if you wish to run authenticated tests (optional for local mock testing).

### 4. Running the Server
Start the FastAPI server locally:
```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Exposing with ngrok
In a new terminal window, run ngrok:
```bash
ngrok http 8000
```
Copy the Forwarding URL (e.g., `https://abc1234.ngrok-free.app`) and set it as the Webhook URL for your Twilio phone number under the **Voice Configuration** section (URL: `https://<your-ngrok-url>/ivr/welcome`, Method: POST).

## Deployed Application
- **Server Status**: [Add Deployment Link Here]
- **Twilio Demo Number**: [Add Twilio Phone Number Here]

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
