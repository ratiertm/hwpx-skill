"""License server — FastAPI."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from . import db
from .keygen import verify_key_format

app = FastAPI(title="HWPX License Server", version="1.0.0")


class VerifyRequest(BaseModel):
    license_key: str
    machine_id: str
    machine_name: Optional[str] = None
    ip_address: Optional[str] = None
    action: Optional[str] = None


class VerifyResponse(BaseModel):
    valid: bool
    message: str
    plan: Optional[str] = None
    expires_at: Optional[str] = None


@app.post("/api/verify", response_model=VerifyResponse)
def verify_license(req: VerifyRequest):
    # 1. Key format check
    if not verify_key_format(req.license_key):
        return VerifyResponse(valid=False, message="Invalid key format")

    # 2. DB lookup
    lic = db.query_one(
        "SELECT * FROM licenses WHERE license_key = %s",
        (req.license_key,),
    )
    if not lic:
        return VerifyResponse(valid=False, message="Key not found")

    if not lic["is_active"]:
        return VerifyResponse(valid=False, message="Key is deactivated")

    if lic["expires_at"] and lic["expires_at"] < datetime.now():
        return VerifyResponse(valid=False, message="Key expired")

    # 3. Device check
    activation = db.query_one(
        "SELECT * FROM activations WHERE license_id = %s AND machine_id = %s",
        (lic["id"], req.machine_id),
    )

    if activation:
        # Update last_seen
        db.execute(
            "UPDATE activations SET last_seen = NOW(), ip_address = %s WHERE id = %s",
            (req.ip_address, activation["id"]),
        )
    else:
        # Check device limit
        active_count = db.query_one(
            "SELECT COUNT(*) as cnt FROM activations WHERE license_id = %s AND is_active = TRUE",
            (lic["id"],),
        )["cnt"]

        if active_count >= lic["max_devices"]:
            return VerifyResponse(
                valid=False,
                message=f"Device limit reached ({lic['max_devices']})",
            )

        # Register new device
        db.execute(
            """INSERT INTO activations (license_id, machine_id, machine_name, ip_address)
               VALUES (%s, %s, %s, %s)""",
            (lic["id"], req.machine_id, req.machine_name, req.ip_address),
        )

    # 4. Log usage
    db.execute(
        """INSERT INTO usage_logs (license_id, machine_id, ip_address, action)
           VALUES (%s, %s, %s, %s)""",
        (lic["id"], req.machine_id, req.ip_address, req.action or "verify"),
    )

    return VerifyResponse(
        valid=True,
        message="OK",
        plan=lic["plan"],
        expires_at=lic["expires_at"].isoformat() if lic["expires_at"] else None,
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
