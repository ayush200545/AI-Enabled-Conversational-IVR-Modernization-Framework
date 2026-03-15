# ============================================================
#  main.py — Entry Point
#  Wires all services together
#
#  Run: uvicorn main:app --reload --port 8000
# ============================================================

from fastapi import FastAPI
from welcome      import router as welcome_router
from menu         import router as menu_router
from ivr_services import router as services_router
from dashboard    import router as dashboard_router

app = FastAPI(
    title="City Hospital IVR System",
    description="Milestone 2 — Welcome Prompt, Menu Driven, Menu Handle, IVR Services, Configuration",
    version="2.0.0"
)

# ── Register all service routers ──────────────────────────────
app.include_router(welcome_router)     # Feature 1: Welcome Prompt
app.include_router(menu_router)        # Feature 2+3: Menu Driven + Handle
app.include_router(services_router)    # Feature 4: Basic IVR Implementation
app.include_router(dashboard_router)   # Feature 5: Configuration Dashboard


# ── Root health check ─────────────────────────────────────────
@app.get("/")
def root():
    return {
        "system":    "City Hospital IVR",
        "milestone": 2,
        "status":    "running",
        "services": {
            "welcome_prompt":    "POST /ivr/welcome",
            "menu_driven":       "POST /ivr/menu",
            "menu_handle":       "POST /ivr/menu  (Digits routing)",
            "admission":         "POST /ivr/admission",
            "bed_status":        "POST /ivr/bed-status",
            "dashboard":         "GET  /dashboard",
        }
    }
