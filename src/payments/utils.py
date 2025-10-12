"""
Utility functions for JazzCash payments
"""

from datetime import datetime, timedelta
import pytz
import random
import string


def generate_txn_ref_no(prefix='T'):
    """
    Generate unique transaction reference number

    Format: T + YYYYMMDDHHMMSS + random 2 digits
    Max length: 20 characters

    Args:
        prefix (str): Prefix for transaction reference

    Returns:
        str: Unique transaction reference number
    """
    # Get current time in Pakistan timezone
    pkt = pytz.timezone('Asia/Karachi')
    now = datetime.now(pkt)

    # Format: TYYYYMMDDHHMMSS + random digits
    timestamp = now.strftime('%Y%m%d%H%M%S')
    random_digits = ''.join(random.choices(string.digits, k=2))

    txn_ref = f"{prefix}{timestamp}{random_digits}"

    # Ensure it doesn't exceed 20 characters
    return txn_ref[:20]


def get_pkt_datetime(dt=None):
    """
    Get datetime in Pakistan timezone

    Args:
        dt (datetime, optional): Datetime object. If None, uses current time.

    Returns:
        datetime: Datetime in PKT timezone
    """
    pkt = pytz.timezone('Asia/Karachi')

    if dt is None:
        return datetime.now(pkt)

    if dt.tzinfo is None:
        # Assume UTC if no timezone
        dt = pytz.utc.localize(dt)

    return dt.astimezone(pkt)


def format_jazzcash_datetime(dt=None):
    """
    Format datetime for JazzCash API (YYYYMMDDHHMMSS)

    Args:
        dt (datetime, optional): Datetime object. If None, uses current time.

    Returns:
        str: Formatted datetime string
    """
    pkt_dt = get_pkt_datetime(dt)
    return pkt_dt.strftime('%Y%m%d%H%M%S')


def get_expiry_datetime(hours=24):
    """
    Get expiry datetime (default 24 hours from now) in JazzCash format

    Args:
        hours (int): Hours to add

    Returns:
        str: Formatted expiry datetime string
    """
    pkt = pytz.timezone('Asia/Karachi')
    now = datetime.now(pkt)
    expiry = now + timedelta(hours=hours)
    return expiry.strftime('%Y%m%d%H%M%S')


def amount_to_paisa(amount):
    """
    Convert amount to paisa (multiply by 100)

    JazzCash requires amount in paisa where last 2 digits are decimal.
    Example: 100.50 PKR = 10050

    Args:
        amount (float or Decimal): Amount in PKR

    Returns:
        int: Amount in paisa
    """
    return int(float(amount) * 100)


def paisa_to_amount(paisa):
    """
    Convert paisa to amount (divide by 100)

    Args:
        paisa (int): Amount in paisa

    Returns:
        float: Amount in PKR
    """
    return float(paisa) / 100


def generate_bill_reference(event_id, user_id):
    """
    Generate bill reference

    Args:
        event_id (int): Event ID
        user_id (int): User ID

    Returns:
        str: Bill reference (max 20 chars)
    """
    timestamp = datetime.now().strftime('%y%m%d%H%M')
    return f"E{event_id}U{user_id}T{timestamp}"[:20]


def validate_cnic(cnic):
    """
    Validate CNIC (last 6 digits)

    Args:
        cnic (str): CNIC string

    Returns:
        bool: True if valid, False otherwise
    """
    if not cnic:
        return False

    # Remove any spaces or dashes
    cnic = cnic.replace('-', '').replace(' ', '')

    # Should be 6 digits for JazzCash
    if len(cnic) != 6:
        return False

    # Should be all digits
    return cnic.isdigit()


def validate_mobile_number(mobile):
    """
    Validate Pakistan mobile number format

    Args:
        mobile (str): Mobile number

    Returns:
        bool: True if valid, False otherwise
    """
    if not mobile:
        return False

    # Remove any spaces or dashes
    mobile = mobile.replace('-', '').replace(' ', '').replace('+', '')

    # Should start with 03 and be 11 digits
    # Format: 03XXXXXXXXX
    if not mobile.startswith('03'):
        return False

    if len(mobile) != 11:
        return False

    return mobile.isdigit()


def format_mobile_number(mobile):
    """
    Format mobile number to standard format

    Args:
        mobile (str): Mobile number

    Returns:
        str: Formatted mobile number (03XXXXXXXXX)
    """
    # Remove any spaces, dashes, plus signs
    mobile = mobile.replace('-', '').replace(' ', '').replace('+', '')

    # Remove country code if present (92)
    if mobile.startswith('92'):
        mobile = '0' + mobile[2:]

    # Ensure it starts with 03
    if not mobile.startswith('03'):
        raise ValueError("Invalid mobile number format")

    return mobile


def is_successful_response(response_code):
    """
    Check if response code indicates success

    Args:
        response_code (str): JazzCash response code

    Returns:
        bool: True if successful
    """
    success_codes = ['000', '121']
    return str(response_code) in success_codes


def get_response_status(response_code):
    """
    Get transaction status based on response code

    Args:
        response_code (str): JazzCash response code

    Returns:
        str: Transaction status (completed, failed, pending)
    """
    response_code = str(response_code)

    if response_code in ['000', '121']:
        return 'completed'
    elif response_code in ['199', '999']:
        return 'failed'
    else:
        return 'pending'
