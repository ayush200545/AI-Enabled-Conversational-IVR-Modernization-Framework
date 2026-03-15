"""
Admin Router - Debug & Monitoring Endpoints
Not exposed in production — useful for development and demos.
"""

from fastapi import APIRouter
from ..services.session_manager import get_all_sessions
from ..data.hospital_db import (
    get_all_wards, get_total_hospital_stats, get_wards_with_availability,
    PATIENTS, ADMISSION_REQUESTS
)
from ..middleware.twilio_security import get_security_status

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/status")
def system_status():
    """Overall hospital + IVR system status."""
    stats = get_total_hospital_stats()
    return {
        "system": "City General Hospital IVR",
        "milestone": "3 - Conversational AI Layer",
        "subtopic": "Patient Admission & Bed Availability Management",
        "hospital_stats": stats,
        "active_calls": len(get_all_sessions()),
        "pending_admissions": len(ADMISSION_REQUESTS),
        "registered_patients": len(PATIENTS),
    }


@router.get("/wards")
def all_wards():
    """View all ward data."""
    return get_all_wards()


@router.get("/beds")
def bed_overview():
    """Bed availability across all wards."""
    stats = get_total_hospital_stats()
    available = get_wards_with_availability()
    return {
        "summary": stats,
        "wards_with_availability": available
    }


@router.get("/patients")
def list_patients():
    """All mock patients."""
    return PATIENTS


@router.get("/admission-requests")
def list_admission_requests():
    """All pending/submitted admission requests."""
    return ADMISSION_REQUESTS


@router.get("/sessions")
def active_sessions():
    """Active IVR call sessions."""
    return get_all_sessions()


@router.get("/security")
def security_config():
    """Twilio webhook security configuration status."""
    return get_security_status()
