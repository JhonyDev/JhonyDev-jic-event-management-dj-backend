#!/usr/bin/env python
"""
Test Hash Calculation for JazzCash
===================================

This script tests the HMAC-SHA256 hash calculation with the provided transaction data
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from src.payments.jazzcash.hmac_utils import generate_secure_hash
from decouple import config

print("=" * 80)
print("JazzCash Hash Calculation Test")
print("=" * 80)
print()

# Transaction data provided
params = {
    'pp_Version': '1.1',
    'pp_TxnType': 'MPAY',
    'pp_Language': 'EN',
    'pp_MerchantID': 'MC392933',
    'pp_SubMerchantID': '',
    'pp_Password': '9a1x3cc9z2',
    'pp_TxnRefNo': 'T2025101413560940',
    'pp_Amount': '50000',
    'pp_TxnCurrency': 'PKR',
    'pp_TxnDateTime': '20251014135609',
    'pp_BillReference': 'E1U2T2510140856',
    'pp_Description': 'Payment for event: FHCC2025',
    'pp_TxnExpiryDateTime': '20251017135609',
    'pp_ReturnURL': 'https://event.jic.agency/api/payments/jazzcash/return/',
    'pp_BankID': '',
    'pp_ProductID': '',
    'ppmpf_1': '',
    'ppmpf_2': '',
    'ppmpf_3': '',
    'ppmpf_4': '',
    'ppmpf_5': ''
}

print("Transaction Parameters:")
print("-" * 80)
for key in sorted(params.keys()):
    value = params[key]
    display_value = f"'{value}'" if value else "(empty)"
    print(f"  {key:25s} = {display_value}")
print()

# Get integrity salt from environment
integrity_salt = config('JAZZCASH_INTEGRITY_SALT', default='')

if not integrity_salt:
    print("❌ ERROR: JAZZCASH_INTEGRITY_SALT not found in environment")
    print("   Please check your .env file")
    sys.exit(1)

print(f"Integrity Salt: {integrity_salt}")
print()

print("Calculating Hash...")
print("-" * 80)
print()

# Calculate hash with empty fields included
calculated_hash = generate_secure_hash(params, integrity_salt, include_empty=True)

print()
print("=" * 80)
print("RESULT:")
print("=" * 80)
print(f"Calculated Hash: {calculated_hash}")
print("=" * 80)
