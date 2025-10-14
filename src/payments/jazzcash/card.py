"""
JazzCash Card Payment Handler (Page Redirection v1.1)
======================================================

Implementation of JazzCash Card Payment integration using Page Redirection
"""

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
    is_successful_response,
)
from ..models import JazzCashTransaction

logger = logging.getLogger(__name__)


class CardPaymentHandler:
    """
    Handler for JazzCash Card Payments (Page Redirection)
    """

    def __init__(self):
        self.config = jazzcash_config
        self.payment_url = self.config.card_url

    def prepare_payment_form(self, event, user, amount, description='', registration=None, session=None, session_registration=None):
        """
        Prepare payment form data for card payment

        Args:
            event: Event object
            user: User object
            amount (Decimal): Amount in PKR
            description (str, optional): Payment description
            registration (Registration, optional): Event registration object
            session (Session, optional): Session object
            session_registration (SessionRegistration, optional): Session registration object

        Returns:
            tuple: (success: bool, form_data: dict, error_message: str)
        """
        try:
            # Generate transaction details
            txn_ref_no = generate_txn_ref_no()
            bill_reference = generate_bill_reference(event.id, user.id)
            amount_in_paisa = amount_to_paisa(amount)

            if not description:
                description = f"Payment for {event.title}"

            # Prepare form parameters
            params = {
                'pp_Version': '1.1',
                'pp_TxnType': 'MPAY',
                'pp_Language': self.config.language,
                'pp_MerchantID': self.config.merchant_id,
                'pp_SubMerchantID': '',
                'pp_Password': self.config.password,
                'pp_TxnRefNo': txn_ref_no,
                'pp_Amount': str(amount_in_paisa),
                'pp_TxnCurrency': self.config.currency,
                'pp_TxnDateTime': format_jazzcash_datetime(),
                'pp_BillReference': bill_reference,
                'pp_Description': description[:200],
                'pp_TxnExpiryDateTime': get_expiry_datetime(72),  # 3 days for card payments
                'pp_ReturnURL': self.config.return_url,
                'pp_BankID': '',
                'pp_ProductID': '',
                'ppmpf_1': '',
                'ppmpf_2': '',
                'ppmpf_3': '',
                'ppmpf_4': '',
                'ppmpf_5': '',
            }

            # Generate secure hash - exclude empty fields
            secure_hash = generate_secure_hash(params, self.config.integrity_salt, include_empty=False)
            params['pp_SecureHash'] = secure_hash

            logger.info(f"Preparing card payment form: {txn_ref_no} for {amount} PKR")

            # Create transaction record
            transaction = JazzCashTransaction.objects.create(
                event=event,
                user=user,
                registration=registration,
                session=session,
                session_registration=session_registration,
                txn_ref_no=txn_ref_no,
                txn_type='MPAY',
                amount=amount,
                amount_in_paisa=amount_in_paisa,
                currency=self.config.currency,
                bill_reference=bill_reference,
                description=description,
                status='pending',
                request_data=params,
            )

            # Return form data
            form_data = {
                'action': self.payment_url,
                'method': 'POST',
                'fields': params,
                'transaction_id': str(transaction.id),
                'txn_ref_no': txn_ref_no,
            }

            return True, form_data, ""

        except Exception as e:
            logger.error(f"Card payment preparation error: {str(e)}", exc_info=True)
            # Try to return txn_ref_no even on error if it was generated
            try:
                return False, {'txn_ref_no': txn_ref_no} if 'txn_ref_no' in locals() else {}, f"Error: {str(e)}"
            except:
                return False, {}, f"Error: {str(e)}"

    def handle_return_response(self, response_data):
        """
        Handle return response from JazzCash

        Args:
            response_data (dict): Response data from JazzCash

        Returns:
            tuple: (success: bool, transaction: JazzCashTransaction, message: str)
        """
        try:
            txn_ref_no = response_data.get('pp_TxnRefNo', '')

            if not txn_ref_no:
                logger.error("No transaction reference in response")
                return False, None, "Invalid response: No transaction reference"

            # Get transaction
            try:
                transaction = JazzCashTransaction.objects.get(txn_ref_no=txn_ref_no)
            except JazzCashTransaction.DoesNotExist:
                logger.error(f"Transaction not found: {txn_ref_no}")
                return False, None, "Transaction not found"

            # Verify secure hash
            received_hash = response_data.get('pp_SecureHash', '')
            response_for_verification = {k: v for k, v in response_data.items() if k != 'pp_SecureHash'}
            is_verified = verify_secure_hash(response_for_verification, received_hash, self.config.integrity_salt)

            if not is_verified:
                logger.error(f"Hash verification failed for transaction {txn_ref_no}")
                transaction.status = 'failed'
                transaction.response_data = response_data
                transaction.save()
                return False, transaction, "Security verification failed"

            # Update transaction with response
            transaction.response_data = response_data
            transaction.pp_response_code = response_data.get('pp_ResponseCode', '')
            transaction.pp_response_message = response_data.get('pp_ResponseMessage', '')
            transaction.pp_retrieval_ref_no = response_data.get('pp_RetreivalReferenceNo', '')
            transaction.pp_auth_code = response_data.get('pp_AuthCode', '')
            transaction.pp_version = response_data.get('pp_Version', '')
            transaction.pp_txn_type = response_data.get('pp_TxnType', '')

            # Check response code
            response_code = response_data.get('pp_ResponseCode', '')

            if is_successful_response(response_code):
                transaction.mark_completed(response_data)
                logger.info(f"Card payment successful: {txn_ref_no}")
                return True, transaction, "Payment successful"
            else:
                transaction.mark_failed(response_data)
                logger.warning(f"Card payment failed: {txn_ref_no} - {response_data.get('pp_ResponseMessage')}")
                return False, transaction, response_data.get('pp_ResponseMessage', 'Payment failed')

        except Exception as e:
            logger.error(f"Error handling return response: {str(e)}", exc_info=True)
            return False, None, f"Error: {str(e)}"

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
