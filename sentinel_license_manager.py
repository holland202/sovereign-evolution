#!/usr/bin/env python3
"""
SENTINEL License Manager
Hardware-bound licensing for commercial deployments.

Generates licenses tied to specific machines.
System refuses to run without valid license.
"""

import os
import hashlib
import hmac
from pathlib import Path
from datetime import datetime, timedelta
from typing import Tuple

class LicenseManager:
    """
    Hardware-bound licensing for SENTINEL.

    License format: {customer}_{hwid}_{expiry}_{signature}
    Example: waterutility-us_a1b2c3d4e5f6_2027-01-15_<sig>
    """

    # No hardcoded fallback: a licensing signature key that defaults to a
    # known public value when unset would let anyone read this file and
    # forge valid licenses. Fail loudly instead of failing open.
    SIGNING_KEY = os.environ.get("SENTINEL_LICENSE_KEY")
    if not SIGNING_KEY:
        raise RuntimeError(
            "SENTINEL_LICENSE_KEY environment variable is not set.\n"
            "This must be a private, random secret. Never hardcode it or "
            "commit it to version control.\n"
            "Generate one with:\n"
            '  python3 -c "import secrets; print(secrets.token_hex(32))"\n'
            "Then set it with:\n"
            "  export SENTINEL_LICENSE_KEY=<the generated value>"
        )

    @staticmethod
    def get_hardware_id() -> str:
        """
        Generate stable hardware fingerprint.
        Uses: CPU serial, OS, hostname, MAC address.
        """
        import socket
        import platform
        import uuid

        components = [
            platform.machine(),  # x86_64, ARM, etc.
            platform.node(),     # hostname
            str(uuid.getnode()),  # MAC address
        ]

        # Create stable hash
        fingerprint = "|".join(components).encode()
        hw_id = hashlib.sha256(fingerprint).hexdigest()[:16]

        return hw_id

    @staticmethod
    def generate_license(
        customer_name: str,
        years: int = 1,
        signing_key: str = None
    ) -> str:
        """Generate a license for a specific customer (no hardware binding yet)."""
        if signing_key is None:
            signing_key = LicenseManager.SIGNING_KEY
        if "_" in customer_name:
            raise ValueError(
                f"customer_name cannot contain underscores (got: {customer_name!r}). "
                "Use hyphens instead, e.g. 'water-utility-us'."
            )

        hw_id = LicenseManager.get_hardware_id()
        expiry = datetime.now() + timedelta(days=365 * years)
        expiry_str = expiry.strftime("%Y-%m-%d")

        # Create license payload
        payload = f"{customer_name}_{hw_id}_{expiry_str}".encode()

        # Sign it
        signature = hmac.new(
            signing_key.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()[:16]

        license_str = f"{customer_name}_{hw_id}_{expiry_str}_{signature}"

        return license_str

    @staticmethod
    def validate_license(
        license_str: str,
        signing_key: str = None
    ) -> Tuple[bool, str]:
        """
        Validate a license string.
        Returns: (is_valid: bool, reason: str)
        """
        if signing_key is None:
            signing_key = LicenseManager.SIGNING_KEY

        try:
            # rsplit from the right: signature, expiry, hw_id are fixed-format
            # and never contain underscores, so this correctly handles
            # customer names that do (unlike a naive left-to-right split).
            parts = license_str.rsplit("_", 3)
            if len(parts) < 4:
                return False, "Invalid license format (too few parts)"

            # Extract components
            customer_name = parts[0]
            hw_id = parts[1]
            expiry_str = parts[2]
            provided_sig = parts[3]

            # Verify hardware match
            current_hw_id = LicenseManager.get_hardware_id()
            if hw_id != current_hw_id:
                return False, f"Hardware mismatch: license bound to {hw_id}, this system is {current_hw_id}"

            # Verify expiry
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d")
            if datetime.now() > expiry:
                return False, f"License expired on {expiry_str}"

            # Verify signature
            payload = f"{customer_name}_{hw_id}_{expiry_str}".encode()
            expected_sig = hmac.new(
                signing_key.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()[:16]

            if not hmac.compare_digest(provided_sig, expected_sig):
                return False, "Invalid signature (license tampered or wrong key)"

            days_left = (expiry - datetime.now()).days
            return True, f"Valid: {customer_name} (expires in {days_left} days)"

        except Exception as e:
            return False, f"License validation error: {str(e)}"

    @staticmethod
    def print_hardware_id():
        """Print this machine's hardware ID (for customer setup)."""
        print(f"Hardware ID: {LicenseManager.get_hardware_id()}")

def require_valid_license():
    """Decorator: only allow SENTINEL to run if a valid license exists.
    Usage: @require_valid_license() above def run_sentinel(): ..."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            license_path = Path.home() / ".sentinel" / "license.txt"
            contact = "Contact: c.holland.arch@proton.me"
            if not license_path.exists():
                raise RuntimeError(f"SENTINEL requires a valid license.\n"
                                    f"Expected at: {license_path}\n{contact}")
            license_str = license_path.read_text().strip()
            is_valid, reason = LicenseManager.validate_license(license_str)
            if not is_valid:
                raise RuntimeError(f"SENTINEL license invalid: {reason}\n{contact}")
            return func(*args, **kwargs)
        return wrapper
    return decorator

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    usage = ("Usage:\n  python3 license_manager.py generate <customer> [years]\n"
             "  python3 license_manager.py validate <license_string>\n"
             "  python3 license_manager.py hwid")

    if not args:
        print(__doc__)
    elif args[0] == "generate" and len(args) >= 2:
        customer, years = args[1], int(args[2]) if len(args) > 2 else 1
        lic = LicenseManager.generate_license(customer, years)
        print(f"\nLicense generated for: {customer}\nLicense string:\n{lic}\n")
        print("Save to: ~/.sentinel/license.txt\n")
    elif args[0] == "validate" and len(args) >= 2:
        is_valid, reason = LicenseManager.validate_license(args[1])
        print(f"{'OK' if is_valid else 'FAIL'}: {reason}")
        sys.exit(0 if is_valid else 1)
    elif args[0] == "hwid":
        LicenseManager.print_hardware_id()
    else:
        print(usage)
