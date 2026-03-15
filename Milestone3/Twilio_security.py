"""
Twilio Webhook Security Middleware
===================================
Validates every incoming request to /ivr/* endpoints is genuinely from Twilio.

How Twilio Signing Works:
    1. Twilio computes: HMAC-SHA1(auth_token, full_url + sorted_post_params)
    2. Twilio sends this signature in the X-Twilio-Signature header
    3. We recompute the same HMAC and compare — if they match, request is real

Why This Matters:
    Without validation, anyone who discovers your ngrok URL can:
    - Trigger fake calls and waste your Twilio credits
    - Inject malicious SpeechResult payloads to manipulate IVR flow
    - Enumerate patient data by forging patient-status requests

Modes:
    - ENFORCE  (production): rejects invalid signatures with HTTP 403
    - LOG_ONLY (staging):    logs warning but allows request through
    - DISABLED (development): skips validation entirely (no TWILIO_AUTH_TOKEN set)

Usage:
    # In main.py — add BEFORE including routers:
    from milestone3.middleware.twilio_security import TwilioSignatureMiddleware
    app.add_middleware(TwilioSignatureMiddleware)
"""

import os
import hmac
import hashlib
import base64
import logging
import time
from urllib.parse import urlencode

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("hospital_ivr.security")

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────

# Which URL prefixes require Twilio signature validation
PROTECTED_PREFIXES = ("/ivr/",)

# Paths exempt from validation even under /ivr/ (e.g. health check)
EXEMPT_PATHS = {"/ivr/health"}

# Validation mode — set via environment variable TWILIO_VALIDATION_MODE
#   "enforce"  → hard reject on invalid signature (production)
#   "log_only" → warn but pass through (staging/testing)
#   "disabled" → skip entirely (local dev, no auth token)
_mode_env = os.getenv("TWILIO_VALIDATION_MODE", "").lower()
_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()

if not _auth_token:
    VALIDATION_MODE = "disabled"
elif _mode_env in ("enforce", "log_only"):
    VALIDATION_MODE = _mode_env
else:
    # Default: enforce if auth token present, disabled otherwise
    VALIDATION_MODE = "enforce" if _auth_token else "disabled"


# ─────────────────────────────────────────────
#  SIGNATURE COMPUTATION
# ─────────────────────────────────────────────

def _compute_signature(auth_token: str, url: str, post_params: dict) -> str:
    """
    Reproduce Twilio's HMAC-SHA1 signature.

    Algorithm:
        1. Start with the full URL (including https://)
        2. Sort POST params alphabetically by key
        3. Append each key+value directly to the URL string (no separators)
        4. HMAC-SHA1 with auth_token as the key
        5. Base64-encode the result
    """
    # Step 1 & 2: URL + sorted params concatenated
    s = url
    if post_params:
        for key in sorted(post_params.keys()):
            s += key + (post_params[key] or "")

    # Step 3: HMAC-SHA1
    mac = hmac.new(
        auth_token.encode("utf-8"),
        s.encode("utf-8"),
        hashlib.sha1,
    )

    # Step 4: Base64
    return base64.b64encode(mac.digest()).decode("utf-8")


def _constant_time_compare(a: str, b: str) -> bool:
    """Timing-safe string comparison — prevents timing attacks."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


# ─────────────────────────────────────────────
#  URL RECONSTRUCTION
# ─────────────────────────────────────────────

def _reconstruct_url(request: Request) -> str:
    """
    Reconstruct the full public URL that Twilio used when it sent the request.

    Important: If behind a reverse proxy / ngrok, the URL must match what
    Twilio sees — i.e. the public https:// URL, not localhost:8000.

    Reads X-Forwarded-Proto and X-Forwarded-Host headers set by ngrok/proxies.
    """
    # Prefer forwarded headers (set by ngrok, nginx, etc.)
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host  = request.headers.get("x-forwarded-host")  or request.headers.get("host") or request.url.netloc
    path  = request.url.path

    # Include query string if present
    query = request.url.query
    full_url = f"{proto}://{host}{path}"
    if query:
        full_url += f"?{query}"

    return full_url


# ─────────────────────────────────────────────
#  REQUEST VALIDATOR
# ─────────────────────────────────────────────

async def validate_twilio_request(request: Request) -> tuple[bool, str]:
    """
    Validate a single request against Twilio's signature.

    Returns:
        (is_valid: bool, reason: str)
    """
    # Get Twilio's signature from header
    twilio_sig = request.headers.get("x-twilio-signature", "")
    if not twilio_sig:
        return False, "Missing X-Twilio-Signature header"

    # Read and cache body (FastAPI body can only be read once)
    body_bytes = await request.body()

    # Parse POST params
    post_params: dict = {}
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        from urllib.parse import parse_qs, unquote_plus
        raw = body_bytes.decode("utf-8")
        for pair in raw.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                post_params[unquote_plus(k)] = unquote_plus(v)

    # Reconstruct public URL
    url = _reconstruct_url(request)

    # Compute expected signature
    expected = _compute_signature(_auth_token, url, post_params)

    # Timing-safe comparison
    if _constant_time_compare(twilio_sig, expected):
        return True, "Valid"

    # Log details for debugging (never log auth_token itself)
    logger.debug(
        f"Signature mismatch | "
        f"URL used: {url} | "
        f"Params: {list(post_params.keys())} | "
        f"Received: {twilio_sig[:12]}... | "
        f"Expected: {expected[:12]}..."
    )
    return False, f"Signature mismatch for URL: {url}"


# ─────────────────────────────────────────────
#  MIDDLEWARE CLASS
# ─────────────────────────────────────────────

class TwilioSignatureMiddleware(BaseHTTPMiddleware):
    """
    Starlette/FastAPI middleware that validates Twilio webhook signatures.

    Add to your FastAPI app BEFORE including IVR routers:

        app.add_middleware(TwilioSignatureMiddleware)

    The middleware only activates on paths matching PROTECTED_PREFIXES
    and respects VALIDATION_MODE (enforce / log_only / disabled).
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        logger.info(
            f"🔒 TwilioSignatureMiddleware loaded | "
            f"Mode: {VALIDATION_MODE.upper()} | "
            f"Auth token: {'SET' if _auth_token else 'NOT SET'}"
        )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # ── Skip non-IVR paths ──────────────────────────────
        if not any(path.startswith(p) for p in PROTECTED_PREFIXES):
            return await call_next(request)

        # ── Skip exempt paths ──────────────────────────────
        if path in EXEMPT_PATHS:
            return await call_next(request)

        # ── Skip GET requests (Twilio only POSTs) ──────────
        if request.method == "GET":
            return await call_next(request)

        # ── Disabled mode — pass through ───────────────────
        if VALIDATION_MODE == "disabled":
            logger.debug(f"[SECURITY] Validation disabled — passing {path}")
            return await call_next(request)

        # ── Validate ───────────────────────────────────────
        start = time.monotonic()
        is_valid, reason = await validate_twilio_request(request)
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)

        call_sid = request.headers.get("x-twilio-callsid", "unknown")[:16]

        if is_valid:
            logger.info(
                f"[SECURITY ✅] Valid Twilio request | "
                f"Path: {path} | CallSid: {call_sid} | {elapsed_ms}ms"
            )
            return await call_next(request)

        # ── Invalid signature ──────────────────────────────
        logger.warning(
            f"[SECURITY ❌] INVALID signature | "
            f"Path: {path} | "
            f"IP: {request.client.host if request.client else 'unknown'} | "
            f"Reason: {reason} | {elapsed_ms}ms"
        )

        if VALIDATION_MODE == "log_only":
            # Warn but allow through (useful for staging)
            logger.warning("[SECURITY] LOG_ONLY mode — allowing despite invalid signature")
            return await call_next(request)

        # ENFORCE mode — reject
        return Response(
            content="Forbidden: Invalid Twilio signature",
            status_code=403,
            media_type="text/plain",
        )


# ─────────────────────────────────────────────
#  STANDALONE VALIDATOR (for unit tests)
# ─────────────────────────────────────────────

def compute_test_signature(auth_token: str, url: str, params: dict) -> str:
    """
    Utility to generate a valid test signature.
    Use this in your test suite to create properly signed mock requests.

    Example:
        sig = compute_test_signature(
            auth_token="test_token_abc",
            url="https://abc.ngrok.io/ivr/intent",
            params={"CallSid": "CA123", "SpeechResult": "ICU beds"}
        )
        headers = {"X-Twilio-Signature": sig}
        # Now send this as a mock Twilio request
    """
    return _compute_signature(auth_token, url, params)


def get_security_status() -> dict:
    """Return current security configuration (safe to expose via admin endpoint)."""
    return {
        "validation_mode": VALIDATION_MODE,
        "auth_token_configured": bool(_auth_token),
        "protected_prefixes": list(PROTECTED_PREFIXES),
        "exempt_paths": list(EXEMPT_PATHS),
        "recommendation": (
            "Production-ready ✅" if VALIDATION_MODE == "enforce" and _auth_token
            else "Set TWILIO_AUTH_TOKEN and TWILIO_VALIDATION_MODE=enforce for production ⚠️"
        )
    }
