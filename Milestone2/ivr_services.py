# ============================================================
#  ivr_services.py — MILESTONE 2: Feature 4
#  Basic IVR Implementation
#  Service A: Patient Admission
#  Service B: Bed Availability Check
# ============================================================

from fastapi import APIRouter, Form
from fastapi.responses import Response
import database as db

router = APIRouter()

def xml(content: str):
    return Response(content=content, media_type="application/xml")

DEPT_MAP = {
    "1": "general",
    "2": "icu",
    "3": "maternity"
}


# ============================================================
#  SERVICE A — PATIENT ADMISSION
# ============================================================
@router.post("/ivr/admission")
async def process_admission(
    Digits: str = Form(...),
    CallSid: str = Form(...),
    From: str = Form(...)
):
    # Go back to main menu
    if Digits == "0":
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Gather numDigits="1" action="/ivr/menu" method="POST">
                <Say voice="Polly.Aditi" language="en-IN">
                    Returning to main menu.
                    Press 1 for Admission.
                    Press 2 for Bed Availability.
                    Press 3 for Emergency.
                    Press 9 for Reception.
                </Say>
            </Gather>
        </Response>"""
        return xml(twiml)

    dept = DEPT_MAP.get(Digits)

    if not dept:
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Gather numDigits="1" action="/ivr/admission" method="POST">
                <Say voice="Polly.Aditi" language="en-IN">
                    Invalid selection.
                    Press 1 for General Ward.
                    Press 2 for I C U.
                    Press 3 for Maternity Ward.
                </Say>
            </Gather>
        </Response>"""
        return xml(twiml)

    # Check bed availability
    if db.bed_data[dept]["available"] > 0:
        # ✅ Reserve a bed
        db.bed_data[dept]["available"] -= 1
        patient_id = db.generate_patient_id()
        spaced_id  = ' '.join(patient_id)

        # Save admission record
        db.admissions.append({
            "patient_id": patient_id,
            "caller":     From,
            "department": dept,
            "time":       __import__('datetime').datetime.now().strftime("%H:%M:%S"),
        })

        # Log it
        db.log_call(
            caller=From,
            action="admission",
            department=dept,
            status="confirmed",
            patient_id=patient_id
        )

        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="Polly.Aditi" language="en-IN">
                Admission confirmed in {dept} ward.
                Your Patient I D is {spaced_id}.
                Please note this ID for future reference.
                A bed has been successfully reserved for you.
                Kindly report to the {dept} ward reception on arrival.
                Thank you for choosing City Hospital.
                We wish you a speedy recovery. Goodbye.
            </Say>
            <Hangup/>
        </Response>"""

    else:
        # ❌ No beds available
        db.log_call(
            caller=From,
            action="admission",
            department=dept,
            status="no_beds"
        )

        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="Polly.Aditi" language="en-IN">
                We are sorry. No beds are currently available in {dept} ward.
                Please visit our reception desk for further assistance.
                You may also try checking another ward.
                Thank you for calling City Hospital. Goodbye.
            </Say>
            <Hangup/>
        </Response>"""

    return xml(twiml)


# ============================================================
#  SERVICE B — BED AVAILABILITY CHECK
# ============================================================
@router.post("/ivr/bed-status")
async def check_bed_status(
    Digits: str = Form(...),
    CallSid: str = Form(...),
    From: str = Form(...)
):
    # Go back to main menu
    if Digits == "0":
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Gather numDigits="1" action="/ivr/menu" method="POST">
                <Say voice="Polly.Aditi" language="en-IN">
                    Returning to main menu.
                    Press 1 for Admission.
                    Press 2 for Bed Availability.
                    Press 3 for Emergency.
                    Press 9 for Reception.
                </Say>
            </Gather>
        </Response>"""
        return xml(twiml)

    dept = DEPT_MAP.get(Digits)

    if not dept:
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Gather numDigits="1" action="/ivr/bed-status" method="POST">
                <Say voice="Polly.Aditi" language="en-IN">
                    Invalid selection.
                    Press 1 for General Ward.
                    Press 2 for I C U.
                    Press 3 for Maternity.
                </Say>
            </Gather>
        </Response>"""
        return xml(twiml)

    available = db.bed_data[dept]["available"]
    total     = db.bed_data[dept]["total"]
    occupied  = total - available

    db.log_call(caller=From, action="bed_check", department=dept, status="checked")

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say voice="Polly.Aditi" language="en-IN">
            Bed status for {dept} ward.
            Total beds: {total}.
            Available beds: {available}.
            Occupied beds: {occupied}.
            {"Beds are available. You may proceed with admission." if available > 0 else "All beds are currently occupied. Please try another ward."}
            Thank you. Goodbye.
        </Say>
        <Hangup/>
    </Response>"""

    return xml(twiml)
