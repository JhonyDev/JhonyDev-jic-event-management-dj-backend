#!/usr/bin/env python3
"""
Standalone Hash Calculation Test for JazzCash
==============================================

This script calculates HMAC-SHA256 hash without requiring Django
"""

import hmac
import hashlib
import os
from pathlib import Path

print("=" * 80)
print("JazzCash Hash Calculation Test (Standalone)")
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

# Try to read integrity salt from .env file
integrity_salt = None
env_file = Path(__file__).parent / '.env'

if env_file.exists():
    print(f"Reading .env file: {env_file}")
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('JAZZCASH_INTEGRITY_SALT='):
                integrity_salt = line.split('=', 1)[1].strip().strip('"').strip("'")
                break

if not integrity_salt:
    # Try environment variable
    integrity_salt = os.environ.get('JAZZCASH_INTEGRITY_SALT', '')

if not integrity_salt:
    print("❌ ERROR: JAZZCASH_INTEGRITY_SALT not found")
    print("   Checked:")
    print(f"   - .env file: {env_file}")
    print("   - Environment variables")
    print()
    print("Please provide integrity salt as argument:")
    print(f"   python3 {Path(__file__).name} YOUR_INTEGRITY_SALT")

    # Check if provided as command line argument
    import sys
    if len(sys.argv) > 1:
        integrity_salt = sys.argv[1]
        print()
        print(f"✓ Using integrity salt from command line argument")
    else:
        print()
        exit(1)

print(f"Integrity Salt: {integrity_salt}")
print()

# Step 1: Filter fields starting with 'pp'
filtered_data = {}
for key, value in params.items():
    if key.lower().startswith('pp'):
        str_value = str(value).strip() if value is not None else ''
        # Include empty fields
        filtered_data[key] = str_value

# Step 2: Sort by key names alphabetically
sorted_keys = sorted(filtered_data.keys())

print("Hash Calculation Steps:")
print("-" * 80)
print(f"Step 1: Filtered data (including empty fields) - {len(filtered_data)} fields")
for key in sorted_keys:
    value = filtered_data[key]
    display = f"'{value}'" if value else "(empty)"
    print(f"  {key} = {display}")
print()

# Step 3: Extract values in sorted order
sorted_values = [filtered_data[key] for key in sorted_keys]

# Step 4: Concatenate with '&' separator
concatenated_string = '&'.join(sorted_values)
print(f"Step 2: Concatenated string ({len(sorted_values)} values):")
print(f"  {concatenated_string}")
print()

# Step 5: Prepend integrity salt
message_to_hash = f"{integrity_salt}&{concatenated_string}"
print(f"Step 3: Message with salt prepended:")
print(f"  {message_to_hash}")
print()

# Step 6: Calculate HMAC-SHA256
hash_object = hmac.new(
    key=integrity_salt.encode('utf-8'),
    msg=message_to_hash.encode('utf-8'),
    digestmod=hashlib.sha256
)

# Get hexadecimal digest in UPPERCASE
calculated_hash = hash_object.hexdigest().upper()

print(f"Step 4: Calculate HMAC-SHA256 using salt as secret key")
print()

print("=" * 80)
print("RESULT:")
print("=" * 80)
print(f"Calculated Hash: {calculated_hash}")
print("=" * 80)
print()
print("✓ Hash calculation complete!")
