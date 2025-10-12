#!/usr/bin/env python
"""
Verify JazzCash Configuration
Checks if credentials are properly loaded from .env file
"""

import sys
import os
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from decouple import config
from src.payments.jazzcash.config import jazzcash_config

print("=" * 80)
print("JazzCash Configuration Verification")
print("=" * 80)

# Check .env file values directly
print("\n1. Values from .env file (using decouple):")
print("-" * 80)
env_merchant_id = config('JAZZCASH_MERCHANT_ID', default='NOT_SET')
env_password = config('JAZZCASH_PASSWORD', default='NOT_SET')
env_salt = config('JAZZCASH_INTEGRITY_SALT', default='NOT_SET')
env_environment = config('JAZZCASH_ENVIRONMENT', default='NOT_SET')

print(f"JAZZCASH_MERCHANT_ID:      {env_merchant_id}")
print(f"JAZZCASH_PASSWORD:         {env_password}")
print(f"JAZZCASH_INTEGRITY_SALT:   {env_salt}")
print(f"JAZZCASH_ENVIRONMENT:      {env_environment}")

# Check Django settings
print("\n2. Values from Django settings:")
print("-" * 80)
from django.conf import settings
jazzcash_settings = getattr(settings, 'JAZZCASH_CONFIG', {})
print(f"MERCHANT_ID:      {jazzcash_settings.get('MERCHANT_ID', 'NOT_SET')}")
print(f"PASSWORD:         {jazzcash_settings.get('PASSWORD', 'NOT_SET')}")
print(f"INTEGRITY_SALT:   {jazzcash_settings.get('INTEGRITY_SALT', 'NOT_SET')}")
print(f"ENVIRONMENT:      {jazzcash_settings.get('ENVIRONMENT', 'NOT_SET')}")

# Check JazzCashConfig class
print("\n3. Values from JazzCashConfig instance (used by MWallet):")
print("-" * 80)
print(f"merchant_id:      {jazzcash_config.merchant_id}")
print(f"password:         {jazzcash_config.password}")
print(f"integrity_salt:   {jazzcash_config.integrity_salt}")
print(f"environment:      {jazzcash_config.environment}")
print(f"mwallet_url:      {jazzcash_config.mwallet_url}")

# Verification
print("\n4. Verification:")
print("-" * 80)
all_match = (
    env_merchant_id == jazzcash_config.merchant_id and
    env_password == jazzcash_config.password and
    env_salt == jazzcash_config.integrity_salt
)

if all_match and env_merchant_id != 'NOT_SET':
    print("✓ SUCCESS: All credentials are properly loaded from .env file")
    print("✓ MWalletClient will use these credentials for payments")
else:
    print("✗ ERROR: Configuration mismatch or missing values!")
    print("  Please check your .env file")

# Expected values from sandbox
print("\n5. Expected Sandbox Values:")
print("-" * 80)
print("JAZZCASH_MERCHANT_ID should be:      MC392933")
print("JAZZCASH_PASSWORD should be:         9a1x3cc9z2")
print("JAZZCASH_INTEGRITY_SALT should be:   wb449x1201")

matches_sandbox = (
    jazzcash_config.merchant_id == 'MC392933' and
    jazzcash_config.password == '9a1x3cc9z2' and
    jazzcash_config.integrity_salt == 'wb449x1201'
)

if matches_sandbox:
    print("\n✓ Using Sandbox Credentials")
else:
    print("\n⚠ Using Different Credentials (Production or Custom)")

print("\n" + "=" * 80)
