import time
import uuid
import requests
from django.conf import settings
from django.core.cache import cache


# ─────────────────────────────────────────────────────────────
# AUTH TOKEN
# ─────────────────────────────────────────────────────────────

def get_access_token() -> str:
    """
    Fetch & cache PhonePe OAuth access token.
    Token is reused until expiry (minus 60s buffer).
    """
    cache_key = "phonepe_access_token"
    cached = cache.get(cache_key)
    if cached:
        return cached

    response = requests.post(
        settings.PHONEPE_AUTH_URL,
        data={
            "client_id": settings.PHONEPE_CLIENT_ID,
            "client_version": settings.PHONEPE_CLIENT_VERSION,
            "client_secret": settings.PHONEPE_CLIENT_SECRET,
            "grant_type": "client_credentials",
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "accept": "application/json",
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    access_token = data["access_token"]
    expires_at = data.get("expires_at")

    ttl = int(expires_at - time.time()) - 60 if expires_at else 3600
    if ttl > 0:
        cache.set(cache_key, access_token, timeout=ttl)

    return access_token


# ─────────────────────────────────────────────────────────────
# PAYMENT INITIATION
# ─────────────────────────────────────────────────────────────

def generate_order_id() -> str:
    return "ORD-" + uuid.uuid4().hex[:20].upper()


def initiate_phonepe_payment(amount_paise: int, merchant_order_id: str, redirect_url: str) -> dict:
    """
    Initiate a PhonePe v2 payment.

    Returns:
        {
            "success": bool,
            "redirect_url": str | None,
            "message": str
        }
    """
    try:
        access_token = get_access_token()
    except Exception as e:
        return {"success": False, "redirect_url": None, "message": f"Auth error: {e}"}

    try:
        response = requests.post(
            settings.PHONEPE_PAYMENT_URL,
            json={
                "merchantOrderId": merchant_order_id,
                "amount": amount_paise,
                "redirectUrl": redirect_url,
                "paymentFlow": {"type": "PG_CHECKOUT"},
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"O-Bearer {access_token}",
            },
            timeout=30,
        )
        data = response.json()

        if response.status_code == 200 and data.get("redirectUrl"):
            return {"success": True, "redirect_url": data["redirectUrl"], "message": "Initiated"}

        return {
            "success": False,
            "redirect_url": None,
            "message": data.get("message", "Payment initiation failed."),
        }

    except requests.exceptions.RequestException as e:
        return {"success": False, "redirect_url": None, "message": f"Network error: {e}"}


# ─────────────────────────────────────────────────────────────
# ORDER STATUS VERIFICATION
# ─────────────────────────────────────────────────────────────

def verify_payment_status(merchant_order_id: str) -> dict:
    """
    Verify payment status from PhonePe using merchant order ID.

    Returns:
        {
            "success": bool,
            "state": "COMPLETED" | "PENDING" | "FAILED",
            "raw": dict
        }
    """
    try:
        access_token = get_access_token()
    except Exception as e:
        return {"success": False, "state": "FAILED", "raw": {}, "message": str(e)}

    try:
        url = f"{settings.PHONEPE_ORDER_STATUS_URL}/{settings.PHONEPE_CLIENT_ID}/{merchant_order_id}"
        response = requests.get(
            url,
            headers={
                "Authorization": f"O-Bearer {access_token}",
                "accept": "application/json",
            },
            timeout=30,
        )
        data = response.json()
        state = data.get("state", "FAILED")
        return {"success": state == "COMPLETED", "state": state, "raw": data}

    except requests.exceptions.RequestException as e:
        return {"success": False, "state": "FAILED", "raw": {}, "message": str(e)}