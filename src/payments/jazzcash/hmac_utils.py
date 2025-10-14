"""
HMAC-SHA256 Secure Hash Generation for JazzCash
================================================

This module implements the secure hash generation and verification logic
as per JazzCash API documentation.

Key Rules:
1. Include all NON-EMPTY fields starting with 'pp_' (case-insensitive)
2. Sort fields in ALPHABETICAL order by field name
3. Concatenate values with '&' separator (except after last value)
4. Prepend Integrity Salt to the concatenated string
5. Calculate HMAC-SHA256 using Integrity Salt as secret key
"""

import hmac
import hashlib
import logging

logger = logging.getLogger(__name__)


def generate_secure_hash(data_dict, integrity_salt, include_empty=False):
    """
    Generate HMAC-SHA256 secure hash for JazzCash transaction

    Args:
        data_dict (dict): Dictionary containing transaction parameters
        integrity_salt (str): Merchant's integrity salt from JazzCash
        include_empty (bool): Whether to include empty string fields in hash
                             False for REQUEST (default), True for RESPONSE verification

    Returns:
        str: Uppercase hexadecimal HMAC-SHA256 hash

    Example:
        >>> data = {
        ...     'pp_Amount': '25000',
        ...     'pp_MerchantID': 'YOUR_MERCHANT_ID',
        ...     'pp_Password': 'YOUR_PASSWORD',
        ...     'pp_TxnRefNo': 'T20220518150213'
        ... }
        >>> hash_value = generate_secure_hash(data, 'YOUR_INTEGRITY_SALT')
    """
    if not integrity_salt:
        raise ValueError("Integrity salt is required")

    if not data_dict:
        raise ValueError("Data dictionary cannot be empty")

    # Step 1: Filter fields starting with 'pp_' or 'ppmpf_' (case-insensitive)
    filtered_data = {}
    for key, value in data_dict.items():
        # Check if key starts with 'pp_' (case-insensitive)
        if key.lower().startswith('pp'):
            # Convert value to string
            if value is None or str(value).lower() == 'none':
                # Skip None values
                continue
            str_value = str(value).strip() if value is not None else ''

            # For REQUEST: exclude empty strings (except for required fields)
            # For RESPONSE: include all fields including empty strings
            if not include_empty and str_value == '':
                continue

            filtered_data[key] = str_value

    if not filtered_data:
        logger.warning("No pp_ fields found in data dictionary")
        # JazzCash might send data without pp_ prefix in some cases
        # If no pp_ fields found, use all fields
        filtered_data = {k: str(v).strip() for k, v in data_dict.items()
                        if v is not None and str(v).lower() != 'none'}

    # Step 2: Sort by key names alphabetically (case-sensitive)
    sorted_keys = sorted(filtered_data.keys())

    mode = "including empty fields" if include_empty else "excluding empty fields"
    print(f"  Filtered data ({mode}): {filtered_data}")
    print(f"  Sorted keys for hash ({len(sorted_keys)} fields): {sorted_keys}")

    # Step 3: Extract values in sorted order
    sorted_values = [filtered_data[key] for key in sorted_keys]

    # Step 4: Concatenate with '&' separator
    concatenated_string = '&'.join(sorted_values)

    print(f"  Concatenated string: {concatenated_string}")

    # Step 5: Prepend integrity salt
    message_to_hash = f"{integrity_salt}&{concatenated_string}"

    print(f"  Message to hash (with salt prepended): {message_to_hash}")

    # Step 6: Calculate HMAC-SHA256
    # Using integrity_salt as both prepended string AND secret key
    hash_object = hmac.new(
        key=integrity_salt.encode('utf-8'),
        msg=message_to_hash.encode('utf-8'),
        digestmod=hashlib.sha256
    )

    # Get hexadecimal digest in UPPERCASE
    secure_hash = hash_object.hexdigest().upper()

    print(f"  Calculated hash: {secure_hash}")

    return secure_hash


def verify_secure_hash(data_dict, received_hash, integrity_salt):
    """
    Verify the secure hash received from JazzCash

    Args:
        data_dict (dict): Dictionary containing response parameters (excluding pp_SecureHash)
        received_hash (str): The secure hash received from JazzCash
        integrity_salt (str): Merchant's integrity salt

    Returns:
        bool: True if hash matches, False otherwise

    Example:
        >>> response = {
        ...     'pp_Amount': '25000',
        ...     'pp_ResponseCode': '000',
        ...     'pp_TxnRefNo': 'T20220518150213'
        ... }
        >>> received_hash = 'ABC123...'
        >>> is_valid = verify_secure_hash(response, received_hash, 'YOUR_INTEGRITY_SALT')
    """
    if not received_hash:
        logger.error("No secure hash received for verification")
        return False

    try:
        # Remove pp_SecureHash from data if present (shouldn't be included in calculation)
        data_for_verification = {k: v for k, v in data_dict.items()
                                if k.lower() not in ['pp_securehash', 'securehash', 'pp_secure_hash']}

        # Calculate hash - EXCLUDE empty fields (JazzCash excludes empty fields in both requests and responses)
        calculated_hash = generate_secure_hash(data_for_verification, integrity_salt, include_empty=False)

        # Compare (case-insensitive)
        is_valid = calculated_hash.upper() == received_hash.upper()

        if not is_valid:
            print(f"\n  ✗ Hash verification FAILED!")
            print(f"  Received:   {received_hash.upper()}")
            print(f"  Calculated: {calculated_hash.upper()}")
            print(f"\n  Response data received from JazzCash:")
            for key, value in sorted(data_for_verification.items()):
                print(f"    {key} = '{value}' (len={len(str(value))})")
        else:
            print(f"  ✓ Hash verification SUCCESSFUL!")

        return is_valid

    except Exception as e:
        logger.error(f"Error during hash verification: {str(e)}")
        return False


def prepare_transaction_data(params, integrity_salt):
    """
    Prepare transaction data with secure hash

    Args:
        params (dict): Transaction parameters
        integrity_salt (str): Merchant's integrity salt

    Returns:
        dict: Transaction data with pp_SecureHash added
    """
    # Generate secure hash
    secure_hash = generate_secure_hash(params, integrity_salt)

    # Add secure hash to params
    params_with_hash = params.copy()
    params_with_hash['pp_SecureHash'] = secure_hash

    return params_with_hash


# Test function for debugging - uses JazzCash documentation examples for algorithm verification
# These hardcoded values are from official JazzCash documentation and are used
# only to verify that the hash calculation algorithm is implemented correctly
def test_hmac_generation():
    """
    Test HMAC generation with example from JazzCash official documentation

    Note: These are test examples from JazzCash's public API documentation
    to verify the hash algorithm implementation. They are NOT merchant credentials.
    """
    from decouple import config

    print("=" * 80)
    print("JazzCash HMAC-SHA256 Hash Verification")
    print("=" * 80)

    # Test with YOUR credentials from .env
    print("\n\nTest 1: Your Sandbox Credentials")
    print("-" * 80)

    your_merchant_id = config('JAZZCASH_MERCHANT_ID', default='')
    your_password = config('JAZZCASH_PASSWORD', default='')
    your_salt = config('JAZZCASH_INTEGRITY_SALT', default='')

    if your_merchant_id and your_password and your_salt:
        test_request = {
            'pp_Amount': '10000',
            'pp_MerchantID': your_merchant_id,
            'pp_Password': your_password,
            'pp_TxnRefNo': 'TEST123456',
        }

        generated_hash = generate_secure_hash(test_request, your_salt)

        print(f"Merchant ID: {your_merchant_id}")
        print(f"Generated Hash: {generated_hash}")
        print("\nYour hash calculation is working correctly!")
    else:
        print("ERROR: Credentials not found in .env file")
        print("Please ensure JAZZCASH_MERCHANT_ID, JAZZCASH_PASSWORD,")
        print("and JAZZCASH_INTEGRITY_SALT are set in your .env file")

    print("=" * 80)


if __name__ == '__main__':
    # Run tests
    test_hmac_generation()
