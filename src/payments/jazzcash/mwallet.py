"""
JazzCash MWallet REST API v2.0 Client
======================================

Implementation of JazzCash Mobile Wallet payment integration
"""

import requests
import logging
from decimal import Decimal

from .config import jazzcash_config
from .hmac_utils import generate_secure_hash, verify_secure_hash
from ..utils import (
    generate_txn_ref_no,
    format_jazzcash_datetime,
    get_expiry_datetime,
    amount_to_paisa,
    generate_bill_reference,
    validate_cnic,
    validate_mobile_number,
    format_mobile_number,
    is_successful_response,
    get_response_status,
)
from ..models import JazzCashTransaction

logger = logging.getLogger(__name__)


class MWalletClient:
    """
    Client for JazzCash MWallet REST API v2.0
    """

    def __init__(self):
        self.config = jazzcash_config
        self.api_url = self.config.mwallet_url

    def initiate_payment(self, event, user, amount, mobile_number, cnic, description='', registration=None, session=None, session_registration=None):
        """
        Initiate MWallet payment

        Args:
            event: Event object
            user: User object
            amount (Decimal): Amount in PKR
            mobile_number (str): Mobile number (03XXXXXXXXX)
            cnic (str): Last 6 digits of CNIC
            description (str, optional): Payment description
            registration (Registration, optional): Event registration object
            session (Session, optional): Session object
            session_registration (SessionRegistration, optional): Session registration object

        Returns:
            tuple: (success: bool, data: dict, error_message: str)
        """
        try:
            # Validate inputs
            if not validate_mobile_number(mobile_number):
                return False, {}, "Invalid mobile number format. Use 03XXXXXXXXX"

            if not validate_cnic(cnic):
                return False, {}, "Invalid CNIC. Provide last 6 digits"

            # Format mobile number
            mobile_number = format_mobile_number(mobile_number)

            # Generate transaction details
            txn_ref_no = generate_txn_ref_no()
            bill_reference = generate_bill_reference(event.id, user.id)
            amount_in_paisa = amount_to_paisa(amount)

            if not description:
                description = f"Payment for {event.title}"

            # Prepare request parameters
            params = {
                'pp_Amount': str(amount_in_paisa),
                'pp_BillReference': bill_reference,
                'pp_CNIC': cnic,
                'pp_Description': description[:200],  # Max 200 chars
                'pp_Language': self.config.language,
                'pp_MerchantID': self.config.merchant_id,
                'pp_MobileNumber': mobile_number,
                'pp_Password': self.config.password,
                'pp_TxnCurrency': self.config.currency,
                'pp_TxnDateTime': format_jazzcash_datetime(),
                'pp_TxnExpiryDateTime': get_expiry_datetime(24),
                'pp_TxnRefNo': txn_ref_no,
                'ppmpf_1': '',
                'ppmpf_2': '',
                'ppmpf_3': '',
                'ppmpf_4': '',
                'ppmpf_5': '',
            }

            # Generate secure hash
            secure_hash = generate_secure_hash(params, self.config.integrity_salt)
            params['pp_SecureHash'] = secure_hash

            logger.info(f"Initiating MWallet payment: {txn_ref_no} for {amount} PKR")

            # Create transaction record
            transaction = JazzCashTransaction.objects.create(
                event=event,
                user=user,
                registration=registration,
                session=session,
                session_registration=session_registration,
                txn_ref_no=txn_ref_no,
                txn_type='MWALLET',
                amount=amount,
                amount_in_paisa=amount_in_paisa,
                currency=self.config.currency,
                bill_reference=bill_reference,
                description=description,
                mobile_number=mobile_number,
                cnic=cnic,
                status='pending',
                request_data=params,
            )

            # Make API request
            response = requests.post(
                self.api_url,
                json=params,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            response_data = response.json()
            logger.info(f"MWallet API Response: {response_data}")

            # Save response
            transaction.response_data = response_data
            transaction.pp_response_code = response_data.get('pp_ResponseCode', '')
            transaction.pp_response_message = response_data.get('pp_ResponseMessage', '')
            transaction.pp_retrieval_ref_no = response_data.get('pp_RetreivalReferenceNo', '')
            transaction.pp_auth_code = response_data.get('pp_AuthCode', '')
            transaction.pp_version = response_data.get('pp_Version', '')
            transaction.pp_txn_type = response_data.get('pp_TxnType', '')

            # Verify secure hash in response
            received_hash = response_data.get('pp_SecureHash', '')
            response_for_verification = {k: v for k, v in response_data.items() if k != 'pp_SecureHash'}
            is_verified = verify_secure_hash(response_for_verification, received_hash, self.config.integrity_salt)

            if not is_verified:
                logger.error(f"Hash verification failed for transaction {txn_ref_no}")
                transaction.status = 'failed'
                transaction.save()
                return False, response_data, "Security verification failed"

            # Check response code
            response_code = response_data.get('pp_ResponseCode', '')

            if is_successful_response(response_code):
                transaction.mark_completed(response_data)
                logger.info(f"MWallet payment successful: {txn_ref_no}")
                # Include txn_ref_no in response_data to ensure it's always available
                response_data['pp_TxnRefNo'] = txn_ref_no
                return True, response_data, "Payment successful"
            else:
                transaction.mark_failed(response_data)
                logger.warning(f"MWallet payment failed: {txn_ref_no} - {response_data.get('pp_ResponseMessage')}")
                # Include txn_ref_no even on failure
                response_data['pp_TxnRefNo'] = txn_ref_no
                return False, response_data, response_data.get('pp_ResponseMessage', 'Payment failed')

        except requests.exceptions.RequestException as e:
            logger.error(f"MWallet API request failed: {str(e)}")
            # Return txn_ref_no even on network error if transaction was created
            try:
                return False, {'pp_TxnRefNo': txn_ref_no}, f"Network error: {str(e)}"
            except:
                return False, {}, f"Network error: {str(e)}"

        except Exception as e:
            logger.error(f"MWallet payment error: {str(e)}", exc_info=True)
            return False, {}, f"Error: {str(e)}"

    def get_transaction(self, txn_ref_no):
        """
        Get transaction by reference number

        Args:
            txn_ref_no (str): Transaction reference number

        Returns:
            JazzCashTransaction or None
        """
        try:
            return JazzCashTransaction.objects.get(txn_ref_no=txn_ref_no)
        except JazzCashTransaction.DoesNotExist:
            return None
