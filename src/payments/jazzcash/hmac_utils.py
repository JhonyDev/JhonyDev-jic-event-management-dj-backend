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


def generate_secure_hash(data_dict, integrity_salt):
    """
    Generate HMAC-SHA256 secure hash for JazzCash transaction

    Args:
        data_dict (dict): Dictionary containing transaction parameters
        integrity_salt (str): Merchant's integrity salt from JazzCash

    Returns:
        str: Uppercase hexadecimal HMAC-SHA256 hash

    Example:
        >>> data = {
        ...     'pp_Amount': '25000',
        ...     'pp_MerchantID': 'MC25041',
        ...     'pp_Password': 'sz1v4agvyf',
        ...     'pp_TxnRefNo': 'T20220518150213'
        ... }
        >>> hash_value = generate_secure_hash(data, '3vv9wu3a18')
    """
    if not integrity_salt:
        raise ValueError("Integrity salt is required")

    if not data_dict:
        raise ValueError("Data dictionary cannot be empty")

    # Step 1: Filter fields starting with 'pp_' (case-insensitive) and remove empty values
    filtered_data = {}
    for key, value in data_dict.items():
        # Check if key starts with 'pp_' (case-insensitive)
        if key.lower().startswith('pp_'):
            # Convert value to string and check if not empty
            str_value = str(value).strip() if value is not None else ''
            if str_value:  # Include only non-empty values
                filtered_data[key] = str_value

    if not filtered_data:
        logger.warning("No pp_ fields found in data dictionary")
        # JazzCash might send data without pp_ prefix in some cases
        # If no pp_ fields found, use all non-empty fields
        filtered_data = {k: str(v).strip() for k, v in data_dict.items()
                        if v is not None and str(v).strip()}

    # Step 2: Sort by key names alphabetically (case-sensitive)
    sorted_keys = sorted(filtered_data.keys())

    logger.debug(f"Sorted keys for hash: {sorted_keys}")

    # Step 3: Extract values in sorted order
    sorted_values = [filtered_data[key] for key in sorted_keys]

    # Step 4: Concatenate with '&' separator
    concatenated_string = '&'.join(sorted_values)

    logger.debug(f"Concatenated values: {concatenated_string}")

    # Step 5: Prepend integrity salt
    message_to_hash = f"{integrity_salt}&{concatenated_string}"

    logger.debug(f"Message to hash (with salt prepended): {message_to_hash}")

    # Step 6: Calculate HMAC-SHA256
    # Using integrity_salt as both prepended string AND secret key
    hash_object = hmac.new(
        key=integrity_salt.encode('utf-8'),
        msg=message_to_hash.encode('utf-8'),
        digestmod=hashlib.sha256
    )

    # Get hexadecimal digest in UPPERCASE
    secure_hash = hash_object.hexdigest().upper()

    logger.debug(f"Generated secure hash: {secure_hash}")

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
        >>> is_valid = verify_secure_hash(response, received_hash, '3vv9wu3a18')
    """
    if not received_hash:
        logger.error("No secure hash received for verification")
        return False

    try:
        # Remove pp_SecureHash from data if present (shouldn't be included in calculation)
        data_for_verification = {k: v for k, v in data_dict.items()
                                if k.lower() not in ['pp_securehash', 'securehash', 'pp_secure_hash']}

        # Calculate hash
        calculated_hash = generate_secure_hash(data_for_verification, integrity_salt)

        # Compare (case-insensitive)
        is_valid = calculated_hash.upper() == received_hash.upper()

        if not is_valid:
            logger.error(f"Hash verification failed!")
            logger.error(f"Received:   {received_hash.upper()}")
            logger.error(f"Calculated: {calculated_hash.upper()}")
        else:
            logger.info("Hash verification successful")

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


# Test function for debugging
def test_hmac_generation():
    """
    Test HMAC generation with example from JazzCash documentation
    """
    print("=" * 80)
    print("Testing HMAC-SHA256 Generation")
    print("=" * 80)

    # Example from "How is HMAC-SHA256 calculated.pdf"
    test_data = {
        'pp_Amount': '25000',
        'pp_MerchantID': 'MC25041',
        'pp_MerchantMPIN': '1234',
        'pp_Password': 'sz1v4agvyf',
        'pp_TxnCurrency': 'PKR',
        'pp_TxnRefNo': 'T20220518150213',
    }

    integrity_salt = '3vv9wu3a18'
    expected_hash = '2C595361C2DA0E502D18BFBAA92CF4740330215E5E8AD0CF4489A64E7400B117'

    generated_hash = generate_secure_hash(test_data, integrity_salt)

    print(f"\nTest Data: {test_data}")
    print(f"\nIntegrity Salt: {integrity_salt}")
    print(f"\nExpected Hash:  {expected_hash}")
    print(f"Generated Hash: {generated_hash}")
    print(f"\nMatch: {generated_hash == expected_hash}")
    print("=" * 80)

    # Example 2 from MWallet documentation
    print("\n\nTesting MWallet Example")
    print("=" * 80)

    mwallet_data = {
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

    mwallet_salt = '9208s6wx05'
    mwallet_expected = '39ECAACFC30F9AFA1763B7E61EA33AC75977FB2E849A5EE1EDC4016791F3438F'

    mwallet_generated = generate_secure_hash(mwallet_data, mwallet_salt)

    print(f"\nTest Data: {mwallet_data}")
    print(f"\nIntegrity Salt: {mwallet_salt}")
    print(f"\nExpected Hash:  {mwallet_expected}")
    print(f"Generated Hash: {mwallet_generated}")
    print(f"\nMatch: {mwallet_generated == mwallet_expected}")
    print("=" * 80)


if __name__ == '__main__':
    # Run tests
    test_hmac_generation()
