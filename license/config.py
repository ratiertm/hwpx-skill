"""License system configuration."""
import os

DB_HOST = os.getenv("HWPX_DB_HOST", "lchfkorea.com")
DB_PORT = int(os.getenv("HWPX_DB_PORT", "5432"))
DB_NAME = os.getenv("HWPX_DB_NAME", "hwpx_license")
DB_USER = os.getenv("HWPX_DB_USER", "hwpx_admin")
DB_PASS = os.getenv("HWPX_DB_PASS", "hwpx_lic_2026!")

# HMAC secret for key signing
HMAC_SECRET = os.getenv("HWPX_HMAC_SECRET", "hwpx-license-sign-key-2026")

# License key prefix
KEY_PREFIX = "HWPX"

# Offline grace period (days)
OFFLINE_GRACE_DAYS = 7

# Default max devices per license
DEFAULT_MAX_DEVICES = 2
