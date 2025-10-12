#!/usr/bin/env python
"""
Test script to verify JazzCash hash calculation
This will help debug the hash mismatch issue
"""

import sys
import os
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from src.payments.jazzcash.hmac_utils import generate_secure_hash

print("=" * 80)
print("JazzCash Hash Calculation Test")
print("=" * 80)

# Test 1: MWallet example from JazzCash documentation
print("\n\nTest 1: MWallet Example from JazzCash Documentation")
print("-" * 80)

mwallet_test_data = {
    'pp_amount': '100',
    'pp_bankID': '',
    'pp_billRef': 'billRef3781',
    'pp_cnic': '345678',
    'pp_description': 'Test case description',
    'pp_language': 'EN',
    'pp_merchantID': 'MC32084',
    'pp_mobile': '03123456789',
    'pp_password': 'yy41w5f10e',
    'pp_productID': '',
    'pp_txnCurrency': 'PKR',
    'pp_txnDateTime': '20220124224204',
    'pp_txnExpiryDateTime': '20220125224204',
    'pp_txnRefNo': 'T71608120',
    'ppmpf_1': '',
    'ppmpf_2': '',
    'ppmpf_3': '',
    'ppmpf_4': '',
    'ppmpf_5': '',
}

test_salt = '9208s6wx05'
expected_hash = '39ECAACFC30F9AFA1763B7E61EA33AC75977FB2E849A5EE1EDC4016791F3438F'

generated_hash = generate_secure_hash(mwallet_test_data, test_salt)

print(f"\nIntegrity Salt: {test_salt}")
print(f"\nExpected Hash:  {expected_hash}")
print(f"Generated Hash: {generated_hash}")
print(f"\nResult: {'✓ PASS' if generated_hash == expected_hash else '✗ FAIL'}")

# Test 2: Your actual credentials
print("\n\n" + "=" * 80)
print("Test 2: Your Sandbox Credentials")
print("-" * 80)

from decouple import config

your_merchant_id = config('JAZZCASH_MERCHANT_ID', default='')
your_password = config('JAZZCASH_PASSWORD', default='')
your_salt = config('JAZZCASH_INTEGRITY_SALT', default='')

print(f"\nYour Merchant ID: {your_merchant_id}")
print(f"Your Password: {your_password}")
print(f"Your Integrity Salt: {your_salt}")

# Test with a simple request
test_request = {
    'pp_Amount': '10000',  # 100 PKR in paisa
    'pp_BillReference': 'TEST123',
    'pp_CNIC': '123456',
    'pp_Description': 'Test payment',
    'pp_Language': 'EN',
    'pp_MerchantID': your_merchant_id,
    'pp_MobileNumber': '03001234567',
    'pp_Password': your_password,
    'pp_TxnCurrency': 'PKR',
    'pp_TxnDateTime': '20251013010000',
    'pp_TxnExpiryDateTime': '20251014010000',
    'pp_TxnRefNo': 'T2025101300000001',
}

print(f"\nTest Request Data:")
for key, value in sorted(test_request.items()):
    print(f"  {key}: {value}")

test_hash = generate_secure_hash(test_request, your_salt)
print(f"\nGenerated Hash: {test_hash}")

print("\n" + "=" * 80)
print("Instructions:")
print("1. If Test 1 PASSES, your hash calculation logic is correct")
print("2. Use the hash from Test 2 to verify with JazzCash support")
print("3. Try a payment and check the logs for 'Filtered data' to see")
print("   what fields JazzCash is including in their response hash")
print("=" * 80)
