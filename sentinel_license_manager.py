#!/usr/bin/env python3
"""
SENTINEL License Manager
Hardware-bound licensing for commercial deployments.

Generates licenses tied to specific machines.
System refuses to run without valid license.
"""

import os
import hashlib
import json
import hmac
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

class LicenseManager:
    """
    Hardware-bound licensing for SENTINEL.
    
    License format: {customer}_{hwid}_{expiry}_{signature}
    Example: waterutility-us_a1b2c3d4e5f6_2027-01-15_<sig>
    """
    
    # KEEP THIS SECRET - REPLACE WITH YOUR OWN KEY
    SIGNING_KEY = os.environ.get(
        "SENTINEL_LICENSE_KEY",
        "CHANGE_ME_TO_RANDOM_32_CHAR_STRING_12345678"
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
        signing_key: str = SIGNING_KEY
    ) -> str:
        """Generate a license for a specific customer (no hardware binding yet)."""
        
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
        signing_key: str = SIGNING_KEY
    ) -> Tuple[bool, str]:
        """
        Validate a license string.
        Returns: (is_valid: bool, reason: str)
        """
        
        try:
            parts = license_str.split("_")
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
    """
    Decorator: only allow SENTINEL to run if valid license exists.
    
    Usage:
        @require_valid_license()
        def run_sentinel():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            license_path = Path.home() / ".sentinel" / "license.txt"
            
            if not license_path.exists():
                raise RuntimeError(
                    f"SENTINEL requires a valid license.\n"
                    f"Expected license at: {license_path}\n"
                    f"Contact: c.holland.arch@proton.me"
                )
            
            license_str = license_path.read_text().strip()
            is_valid, reason = LicenseManager.validate_license(license_str)
            
            if not is_valid:
                raise RuntimeError(
                    f"SENTINEL license invalid: {reason}\n"
                    f"Contact: c.holland.arch@proton.me"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "generate":
            if len(sys.argv) < 3:
                print("Usage: python3 license_manager.py generate <customer_name> [years]")
                sys.exit(1)
            
            customer = sys.argv[2]
            years = int(sys.argv[3]) if len(sys.argv) > 3 else 1
            
            license_str = LicenseManager.generate_license(customer, years)
            print(f"\n✅ License generated for: {customer}")
            print(f"License string:\n{license_str}\n")
            print(f"Save to: ~/.sentinel/license.txt\n")
        
        elif sys.argv[1] == "validate":
            if len(sys.argv) < 3:
                print("Usage: python3 license_manager.py validate <license_string>")
                sys.exit(1)
            
            license_str = sys.argv[2]
            is_valid, reason = LicenseManager.validate_license(license_str)
            
            if is_valid:
                print(f"✅ {reason}")
            else:
                print(f"❌ {reason}")
            
            sys.exit(0 if is_valid else 1)
        
        elif sys.argv[1] == "hwid":
            LicenseManager.print_hardware_id()
        
        else:
            print("Usage:")
            print("  python3 license_manager.py generate <customer> [years]")
            print("  python3 license_manager.py validate <license_string>")
            print("  python3 license_manager.py hwid")
    
    else:
        print(__doc__)
