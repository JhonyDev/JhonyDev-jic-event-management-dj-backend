"""
JazzCash Refund API
===================

Process refunds for completed transactions
"""

import requests
import logging
from decimal import Decimal

from .config import jazzcash_config
from .hmac_utils import generate_secure_hash, verify_secure_hash
from ..utils import amount_to_paisa
from ..models import JazzCashTransaction, JazzCashRefund

logger = logging.getLogger(__name__)


class RefundClient:
    """
    Client for JazzCash Refund API
    """

    def __init__(self):
        self.config = jazzcash_config
        self.api_url = self.config.refund_url

    def process_refund(self, txn_ref_no, refund_amount, reason, initiated_by=None):
        """
        Process refund for a transaction

        Args:
            txn_ref_no (str): Original transaction reference number
            refund_amount (Decimal): Amount to refund in PKR
            reason (str): Reason for refund
            initiated_by (User, optional): User initiating refund

        Returns:
            tuple: (success: bool, refund: JazzCashRefund, message: str)
        """
        try:
            # Get original transaction
            try:
                transaction = JazzCashTransaction.objects.get(txn_ref_no=txn_ref_no)
            except JazzCashTransaction.DoesNotExist:
                return False, None, "Transaction not found"

            # Check if refund is allowed
            can_refund, message = transaction.can_refund(refund_amount)
            if not can_refund:
                return False, None, message

            # Convert amount to paisa
            refund_amount_paisa = amount_to_paisa(refund_amount)

            # Prepare request
            params = {
                'pp_TxnRefNo': txn_ref_no,
                'pp_Amount': str(refund_amount_paisa),
                'pp_TxnCurrency': self.config.currency,
                'pp_MerchantID': self.config.merchant_id,
                'pp_Password': self.config.password,
            }

            # Generate secure hash - exclude empty fields
            secure_hash = generate_secure_hash(params, self.config.integrity_salt, include_empty=False)
            params['pp_SecureHash'] = secure_hash

            logger.info(f"Processing refund for {txn_ref_no}: {refund_amount} PKR")

            # Create refund record
            refund = JazzCashRefund.objects.create(
                original_transaction=transaction,
                refund_amount=refund_amount,
                refund_reason=reason,
                initiated_by=initiated_by,
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
            logger.info(f"Refund API Response: {response_data}")

            # Save response
            refund.response_data = response_data
            refund.response_code = response_data.get('responseCode', '')
            refund.response_message = response_data.get('responseMessage', '')
            refund.secure_hash = response_data.get('secureHash', '')

            # Verify secure hash
            received_hash = response_data.get('secureHash', '')
            response_for_verification = {k: v for k, v in response_data.items() if k != 'secureHash'}
            is_verified = verify_secure_hash(response_for_verification, received_hash, self.config.integrity_salt)

            if not is_verified:
                logger.error(f"Hash verification failed for refund: {txn_ref_no}")
                refund.status = 'failed'
                refund.save()
                return False, refund, "Security verification failed"

            # Check response code
            response_code = response_data.get('responseCode', '')

            if response_code == '000':
                refund.mark_completed(response_data)
                logger.info(f"Refund successful for {txn_ref_no}")
                return True, refund, "Refund successful"
            else:
                refund.status = 'failed'
                refund.save()
                message = response_data.get('responseMessage', 'Refund failed')
                logger.warning(f"Refund failed for {txn_ref_no}: {message}")
                return False, refund, message

        except requests.exceptions.RequestException as e:
            logger.error(f"Refund request failed: {str(e)}")
            if 'refund' in locals():
                refund.status = 'failed'
                refund.save()
            return False, None, f"Network error: {str(e)}"

        except Exception as e:
            logger.error(f"Refund error: {str(e)}", exc_info=True)
            if 'refund' in locals():
                refund.status = 'failed'
                refund.save()
            return False, None, f"Error: {str(e)}"

    def get_refund_history(self, txn_ref_no):
        """
        Get refund history for a transaction

        Args:
            txn_ref_no (str): Transaction reference number

        Returns:
            QuerySet: Refunds for the transaction
        """
        try:
            transaction = JazzCashTransaction.objects.get(txn_ref_no=txn_ref_no)
            return transaction.refunds.all()
        except JazzCashTransaction.DoesNotExist:
            return JazzCashRefund.objects.none()
