#!/usr/bin/env python3
"""
Compare Hash Calculation Methods
=================================

This script tests different hash calculation approaches to find the mismatch
"""

import hmac
import hashlib
from pathlib import Path

print("=" * 80)
print("JazzCash Hash Calculation Comparison")
print("=" * 80)
print()

# Transaction data
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

# Read integrity salt
integrity_salt = None
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('JAZZCASH_INTEGRITY_SALT='):
                integrity_salt = line.split('=', 1)[1].strip().strip('"').strip("'")
                break

if not integrity_salt:
    print("❌ ERROR: JAZZCASH_INTEGRITY_SALT not found")
    exit(1)

print(f"Integrity Salt: {integrity_salt}")
print()

def calculate_hash(include_empty, description):
    """Calculate hash with or without empty fields"""
    print("-" * 80)
    print(description)
    print("-" * 80)

    # Filter fields
    filtered_data = {}
    for key, value in params.items():
        if key.lower().startswith('pp'):
            str_value = str(value).strip() if value is not None else ''

            # Include or exclude empty based on parameter
            if not include_empty and str_value == '':
                continue

            filtered_data[key] = str_value

    # Sort and concatenate
    sorted_keys = sorted(filtered_data.keys())
    sorted_values = [filtered_data[key] for key in sorted_keys]
    concatenated_string = '&'.join(sorted_values)
    message_to_hash = f"{integrity_salt}&{concatenated_string}"

    # Calculate HMAC
    hash_object = hmac.new(
        key=integrity_salt.encode('utf-8'),
        msg=message_to_hash.encode('utf-8'),
        digestmod=hashlib.sha256
    )
    calculated_hash = hash_object.hexdigest().upper()

    print(f"Fields included: {len(filtered_data)}")
    print(f"Concatenated: {concatenated_string[:100]}...")
    print(f"Message: {message_to_hash[:100]}...")
    print(f"Hash: {calculated_hash}")
    print()

    return calculated_hash

# Test 1: Including empty fields
hash1 = calculate_hash(True, "Test 1: INCLUDING empty fields (include_empty=True)")

# Test 2: Excluding empty fields
hash2 = calculate_hash(False, "Test 2: EXCLUDING empty fields (include_empty=False)")

# Compare with what user is seeing
user_hash = "3EA1DDD822FF3E741341CA0B13231A5B118F35F48FD594D188F893C51E0AC289"

print("=" * 80)
print("COMPARISON:")
print("=" * 80)
print(f"Hash with empty fields:    {hash1}")
print(f"Hash without empty fields: {hash2}")
print(f"Hash user is seeing:       {user_hash}")
print("=" * 80)

if hash1 == user_hash:
    print("✓ MATCH: Django is INCLUDING empty fields")
elif hash2 == user_hash:
    print("✓ MATCH: Django is EXCLUDING empty fields")
else:
    print("✗ NO MATCH: Hash is different from both methods")
    print()
    print("Possible causes:")
    print("  1. Different integrity salt is being used")
    print("  2. Field values are different (encoding, whitespace, etc.)")
    print("  3. Different fields are being included")
    print("  4. Field order is different")
    print()
    print("Please check your Django logs for the concatenated string")
