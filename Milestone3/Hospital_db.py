"""
Mock Hospital Database
Patient Admission & Bed Availability Management IVR
Milestone 3 - Twilio Conversational AI Layer
"""

from datetime import datetime, timedelta
import random

# ─────────────────────────────────────────────
#  WARD / DEPARTMENT DATA
# ─────────────────────────────────────────────

WARDS = {
    "general": {
        "name": "General Ward",
        "code": "GW",
        "total_beds": 40,
        "available_beds": 12,
        "contact_ext": "101",
        "floor": "Ground Floor",
        "speciality": "General Medicine"
    },
    "icu": {
        "name": "Intensive Care Unit",
        "code": "ICU",
        "total_beds": 10,
        "available_beds": 2,
        "contact_ext": "200",
        "floor": "First Floor",
        "speciality": "Critical Care"
    },
    "emergency": {
        "name": "Emergency Ward",
        "code": "EMR",
        "total_beds": 20,
        "available_beds": 5,
        "contact_ext": "911",
        "floor": "Ground Floor",
        "speciality": "Emergency Medicine"
    },
    "pediatric": {
        "name": "Pediatric Ward",
        "code": "PED",
        "total_beds": 15,
        "available_beds": 7,
        "contact_ext": "305",
        "floor": "Second Floor",
        "speciality": "Pediatrics"
    },
    "maternity": {
        "name": "Maternity Ward",
        "code": "MAT",
        "total_beds": 18,
        "available_beds": 4,
        "contact_ext": "410",
        "floor": "Third Floor",
        "speciality": "Obstetrics & Gynaecology"
    },
    "cardiology": {
        "name": "Cardiology Ward",
        "code": "CAR",
        "total_beds": 12,
        "available_beds": 3,
        "contact_ext": "502",
        "floor": "Second Floor",
        "speciality": "Cardiology"
    },
    "orthopedic": {
        "name": "Orthopedic Ward",
        "code": "ORT",
        "total_beds": 14,
        "available_beds": 6,
        "contact_ext": "601",
        "floor": "Third Floor",
        "speciality": "Orthopedics"
    },
    "neurology": {
        "name": "Neurology Ward",
        "code": "NEU",
        "total_beds": 10,
        "available_beds": 1,
        "contact_ext": "702",
        "floor": "Fourth Floor",
        "speciality": "Neurology"
    },
}

# ─────────────────────────────────────────────
#  MOCK PATIENT RECORDS
# ─────────────────────────────────────────────

PATIENTS = {
    "P1001": {
        "patient_id": "P1001",
        "name": "Rahul Sharma",
        "age": 45,
        "gender": "Male",
        "ward": "cardiology",
        "bed_number": "CAR-04",
        "admission_date": (datetime.now() - timedelta(days=3)).strftime("%d %B %Y"),
        "doctor": "Dr. Meena Iyer",
        "status": "Admitted",
        "diagnosis": "Cardiac Monitoring",
        "contact": "9876543210"
    },
    "P1002": {
        "patient_id": "P1002",
        "name": "Priya Patel",
        "age": 30,
        "gender": "Female",
        "ward": "maternity",
        "bed_number": "MAT-08",
        "admission_date": (datetime.now() - timedelta(days=1)).strftime("%d %B %Y"),
        "doctor": "Dr. Sunita Rao",
        "status": "Admitted",
        "diagnosis": "Maternity Care",
        "contact": "9123456789"
    },
    "P1003": {
        "patient_id": "P1003",
        "name": "Amit Singh",
        "age": 12,
        "gender": "Male",
        "ward": "pediatric",
        "bed_number": "PED-03",
        "admission_date": datetime.now().strftime("%d %B %Y"),
        "doctor": "Dr. Rakesh Kumar",
        "status": "Under Observation",
        "diagnosis": "Viral Fever",
        "contact": "9988776655"
    },
    "P1004": {
        "patient_id": "P1004",
        "name": "Sunita Mehta",
        "age": 65,
        "gender": "Female",
        "ward": "neurology",
        "bed_number": "NEU-02",
        "admission_date": (datetime.now() - timedelta(days=5)).strftime("%d %B %Y"),
        "doctor": "Dr. Arjun Nair",
        "status": "Critical",
        "diagnosis": "Neurological Assessment",
        "contact": "9765432100"
    },
}

# ─────────────────────────────────────────────
#  PENDING ADMISSION REQUESTS (in-memory queue)
# ─────────────────────────────────────────────

ADMISSION_REQUESTS = {}

# ─────────────────────────────────────────────
#  DATABASE HELPER FUNCTIONS
# ─────────────────────────────────────────────

def get_ward_info(ward_key: str) -> dict | None:
    return WARDS.get(ward_key.lower())

def get_all_wards() -> dict:
    return WARDS

def get_bed_availability(ward_key: str = None) -> dict:
    if ward_key:
        ward = WARDS.get(ward_key.lower())
        if not ward:
            return {}
        occupied = ward["total_beds"] - ward["available_beds"]
        return {
            ward_key: {
                **ward,
                "occupied_beds": occupied,
                "occupancy_rate": round((occupied / ward["total_beds"]) * 100, 1)
            }
        }
    # Return all wards with availability
    result = {}
    for key, ward in WARDS.items():
        occupied = ward["total_beds"] - ward["available_beds"]
        result[key] = {
            **ward,
            "occupied_beds": occupied,
            "occupancy_rate": round((occupied / ward["total_beds"]) * 100, 1)
        }
    return result

def find_patient(patient_id: str) -> dict | None:
    return PATIENTS.get(patient_id.upper())

def find_patient_by_name(name: str) -> list[dict]:
    name_lower = name.lower()
    return [p for p in PATIENTS.values() if name_lower in p["name"].lower()]

def create_admission_request(data: dict) -> str:
    req_id = f"REQ{random.randint(10000, 99999)}"
    ADMISSION_REQUESTS[req_id] = {
        **data,
        "request_id": req_id,
        "status": "Pending Review",
        "submitted_at": datetime.now().strftime("%d %B %Y, %I:%M %p")
    }
    return req_id

def get_admission_request(req_id: str) -> dict | None:
    return ADMISSION_REQUESTS.get(req_id.upper())

def get_wards_with_availability() -> list[dict]:
    """Return wards that have at least 1 available bed"""
    return [
        {"key": k, **v}
        for k, v in WARDS.items()
        if v["available_beds"] > 0
    ]

def get_total_hospital_stats() -> dict:
    total = sum(w["total_beds"] for w in WARDS.values())
    available = sum(w["available_beds"] for w in WARDS.values())
    return {
        "total_beds": total,
        "available_beds": available,
        "occupied_beds": total - available,
        "occupancy_rate": round(((total - available) / total) * 100, 1),
        "wards_with_vacancy": sum(1 for w in WARDS.values() if w["available_beds"] > 0)
    }
