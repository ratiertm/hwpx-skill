"""License client — embed in pyhwpxlib."""
import hashlib
import json
import platform
import uuid
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timedelta

LICENSE_FILE = Path.home() / ".pyhwpxlib" / "license.key"
CACHE_FILE = Path.home() / ".pyhwpxlib" / "license.cache"
SERVER_URL = "http://lchfkorea.com:8443/api/verify"
OFFLINE_GRACE_DAYS = 7


def get_machine_id() -> str:
    """Generate a stable machine fingerprint."""
    raw = f"{platform.node()}-{platform.machine()}-{uuid.getnode()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_machine_name() -> str:
    return f"{platform.node()} ({platform.system()} {platform.machine()})"


def activate(license_key: str):
    """Save license key to disk."""
    LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LICENSE_FILE.write_text(license_key.strip())
    print(f"License saved to {LICENSE_FILE}")
    # Verify immediately
    result = check_license(action="activate")
    if result["valid"]:
        print(f"Activated! Plan: {result.get('plan', 'standard')}")
    else:
        print(f"Activation failed: {result['message']}")
    return result


def check_license(action: str = "verify") -> dict:
    """Check license validity. Returns {'valid': bool, 'message': str, ...}"""
    # 1. Read key
    if not LICENSE_FILE.exists():
        return {"valid": False, "message": "No license key. Run: pyhwpxlib.activate('YOUR-KEY')"}

    key = LICENSE_FILE.read_text().strip()
    if not key:
        return {"valid": False, "message": "Empty license key"}

    # 2. Try server
    try:
        result = _server_verify(key, action)
        # Cache successful result
        _save_cache(result)
        return result
    except Exception:
        # 3. Fallback to cache
        return _check_cache()


def _server_verify(key: str, action: str) -> dict:
    """Call license server."""
    payload = json.dumps({
        "license_key": key,
        "machine_id": get_machine_id(),
        "machine_name": get_machine_name(),
        "action": action,
    }).encode()

    req = urllib.request.Request(
        SERVER_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"valid": False, "message": f"Server error: {e.code}"}
    except Exception as e:
        raise ConnectionError(f"Cannot reach license server: {e}")


def _save_cache(result: dict):
    """Cache verification result locally."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    cache = {
        "result": result,
        "cached_at": datetime.now().isoformat(),
    }
    CACHE_FILE.write_text(json.dumps(cache))


def _check_cache() -> dict:
    """Check offline cache."""
    if not CACHE_FILE.exists():
        return {"valid": False, "message": "Server unreachable and no cache"}

    try:
        cache = json.loads(CACHE_FILE.read_text())
        cached_at = datetime.fromisoformat(cache["cached_at"])
        if datetime.now() - cached_at > timedelta(days=OFFLINE_GRACE_DAYS):
            return {"valid": False, "message": f"Cache expired ({OFFLINE_GRACE_DAYS} days)"}
        return cache["result"]
    except Exception:
        return {"valid": False, "message": "Cache corrupted"}


def require_license(func):
    """Decorator to enforce license check on a function."""
    def wrapper(*args, **kwargs):
        result = check_license(action=func.__name__)
        if not result["valid"]:
            raise RuntimeError(f"License error: {result['message']}")
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
