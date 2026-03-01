# ============================================================
#  database.py — In-Memory Data Storage
#  All bed data, call logs, admissions stored here
# ============================================================

from datetime import datetime
import random
import string

# ── BED DATABASE ─────────────────────────────────────────────
bed_data = {
    "general":   {"total": 10, "available": 10, "icon": "🛏️"},
    "icu":       {"total": 5,  "available": 5,  "icon": "🫀"},
    "maternity": {"total": 6,  "available": 6,  "icon": "🍼"},
}

# ── CALL SESSIONS ─────────────────────────────────────────────
sessions = {}

# ── CALL LOGS ─────────────────────────────────────────────────
call_logs = []

# ── ADMISSIONS ────────────────────────────────────────────────
admissions = []

# ── HELPER: Generate Patient ID ───────────────────────────────
def generate_patient_id():
    year = datetime.now().year
    suffix = ''.join(random.choices(string.digits, k=4))
    return f"PAT-{year}-{suffix}"

# ── HELPER: Log a call event ──────────────────────────────────
def log_call(caller, action, department=None, status="ok", patient_id=None):
    call_logs.append({
        "time":       datetime.now().strftime("%H:%M:%S"),
        "date":       datetime.now().strftime("%d %b %Y"),
        "caller":     caller,
        "action":     action,
        "department": department or "—",
        "status":     status,
        "patient_id": patient_id or "—",
    })

# ── HELPER: Get stats summary ────────────────────────────────
def get_stats():
    total_calls    = len(call_logs)
    total_admitted = len([l for l in call_logs if l["action"] == "admission" and l["status"] == "confirmed"])
    emergency      = len([l for l in call_logs if l["action"] == "emergency"])
    bed_checks     = len([l for l in call_logs if l["action"] == "bed_check"])
    return {
        "total_calls":    total_calls,
        "total_admitted": total_admitted,
        "emergency":      emergency,
        "bed_checks":     bed_checks,
    }