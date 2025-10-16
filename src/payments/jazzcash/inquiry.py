"""
JazzCash Status Inquiry API
============================

Check transaction status for pending/missing transactions
"""

import requests
import logging

from .config import jazzcash_config
from .hmac_utils import generate_secure_hash, verify_secure_hash
from ..models import JazzCashTransaction, JazzCashStatusInquiry

logger = logging.getLogger(__name__)


class StatusInquiryClient:
    """
    Client for JazzCash Status Inquiry API
    """

    def __init__(self):
        self.config = jazzcash_config
        self.api_url = self.config.status_inquiry_url

    def inquire_transaction(self, txn_ref_no, inquired_by=None):
        """
        Inquire transaction status

        Note: Should be called minimum 10 minutes after transaction initiation

        Args:
            txn_ref_no (str): Transaction reference number
            inquired_by (User, optional): User making the inquiry

        Returns:
            tuple: (success: bool, data: dict, message: str)
        """
        try:
            # Get transaction
            try:
                transaction = JazzCashTransaction.objects.get(txn_ref_no=txn_ref_no)
            except JazzCashTransaction.DoesNotExist:
                return False, {}, "Transaction not found"

            # Prepare request
            params = {
                'pp_TxnRefNo': txn_ref_no,
                'pp_MerchantID': self.config.merchant_id,
                'pp_Password': self.config.password,
            }

            # Generate secure hash - exclude empty fields
            secure_hash = generate_secure_hash(params, self.config.integrity_salt, include_empty=False)
            params['pp_SecureHash'] = secure_hash

            logger.info(f"Inquiring transaction status: {txn_ref_no}")

            # Make API request
            response = requests.post(
                self.api_url,
                json=params,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            response_data = response.json()
            logger.info(f"Status Inquiry Response: {response_data}")

            # Verify secure hash
            received_hash = response_data.get('pp_SecureHash', '')
            response_for_verification = {k: v for k, v in response_data.items() if k != 'pp_SecureHash'}
            is_verified = verify_secure_hash(response_for_verification, received_hash, self.config.integrity_salt)

            # Create inquiry log
            inquiry = JazzCashStatusInquiry.objects.create(
                transaction=transaction,
                inquired_by=inquired_by,
                request_data=params,
                response_data=response_data,
                response_code=response_data.get('pp_ResponseCode', ''),
                response_message=response_data.get('pp_ResponseMessage', ''),
                payment_response_code=response_data.get('pp_PaymentResponseCode', ''),
                payment_response_message=response_data.get('pp_PaymentResponseMessage', ''),
                payment_status=response_data.get('pp_Status', ''),
                success=is_verified and response_data.get('pp_ResponseCode') == '000',
            )

            if not is_verified:
                logger.error(f"Hash verification failed for inquiry: {txn_ref_no}")
                return False, response_data, "Security verification failed"

            # Check API response code
            api_response_code = response_data.get('pp_ResponseCode', '')
            if api_response_code != '000':
                message = response_data.get('pp_ResponseMessage', 'Inquiry failed')
                return False, response_data, message

            # Check actual payment status
            payment_response_code = response_data.get('pp_PaymentResponseCode', '')
            payment_status = response_data.get('pp_Status', '').lower()

            # Update transaction if status changed
            if payment_response_code == '121' and payment_status == 'completed':
                if transaction.status != 'completed':
                    transaction.mark_completed(response_data)
                    logger.info(f"Transaction {txn_ref_no} marked as completed via inquiry")

                    # Update registration status
                    if transaction.event and transaction.registration:
                        from django.utils import timezone
                        transaction.registration.status = 'confirmed'
                        transaction.registration.payment_status = 'paid'
                        transaction.registration.payment_amount = transaction.amount
                        transaction.registration.payment_date = timezone.now()
                        transaction.registration.save()

                        # Log successful payment
                        from src.api.models import RegistrationLog
                        RegistrationLog.objects.create(
                            event=transaction.event,
                            user=transaction.user,
                            registration=transaction.registration,
                            action='payment_success',
                            email=transaction.user.email,
                            first_name=transaction.user.first_name,
                            last_name=transaction.user.last_name,
                            phone_number=transaction.user.phone_number if hasattr(transaction.user, 'phone_number') else '',
                            registration_type=transaction.registration.registration_type,
                            payment_method=transaction.payment_method,
                            payment_amount=transaction.amount,
                            transaction_reference=transaction.txn_ref_no,
                            notes=f'Payment successful via status inquiry. Response: {response_data.get("pp_PaymentResponseMessage", "")}'
                        )

                        # Log registration completed
                        RegistrationLog.objects.create(
                            event=transaction.event,
                            user=transaction.user,
                            registration=transaction.registration,
                            action='registration_completed',
                            email=transaction.user.email,
                            first_name=transaction.user.first_name,
                            last_name=transaction.user.last_name,
                            phone_number=transaction.user.phone_number if hasattr(transaction.user, 'phone_number') else '',
                            registration_type=transaction.registration.registration_type,
                            payment_method=transaction.payment_method,
                            payment_amount=transaction.amount,
                            transaction_reference=transaction.txn_ref_no,
                            notes=f'Registration completed successfully with payment confirmation (via inquiry)'
                        )

            elif payment_response_code in ['199', '999']:
                if transaction.status != 'failed':
                    transaction.mark_failed(response_data)
                    logger.info(f"Transaction {txn_ref_no} marked as failed via inquiry")

                    # Log failed payment
                    if transaction.event and transaction.registration:
                        from src.api.models import RegistrationLog
                        RegistrationLog.objects.create(
                            event=transaction.event,
                            user=transaction.user,
                            registration=transaction.registration,
                            action='payment_failed',
                            email=transaction.user.email,
                            first_name=transaction.user.first_name,
                            last_name=transaction.user.last_name,
                            phone_number=transaction.user.phone_number if hasattr(transaction.user, 'phone_number') else '',
                            registration_type=transaction.registration.registration_type if transaction.registration else None,
                            payment_method=transaction.payment_method,
                            payment_amount=transaction.amount,
                            transaction_reference=transaction.txn_ref_no,
                            notes=f'Payment failed via status inquiry. Response: {response_data.get("pp_PaymentResponseMessage", "")} (Code: {payment_response_code})'
                        )

                        # Log registration failed
                        RegistrationLog.objects.create(
                            event=transaction.event,
                            user=transaction.user,
                            registration=transaction.registration,
                            action='registration_failed',
                            email=transaction.user.email,
                            first_name=transaction.user.first_name,
                            last_name=transaction.user.last_name,
                            phone_number=transaction.user.phone_number if hasattr(transaction.user, 'phone_number') else '',
                            registration_type=transaction.registration.registration_type if transaction.registration else None,
                            payment_method=transaction.payment_method,
                            payment_amount=transaction.amount,
                            transaction_reference=transaction.txn_ref_no,
                            notes=f'Registration failed due to payment failure (via inquiry)'
                        )

            return True, response_data, "Inquiry successful"

        except requests.exceptions.RequestException as e:
            logger.error(f"Status inquiry request failed: {str(e)}")
            return False, {}, f"Network error: {str(e)}"

        except Exception as e:
            logger.error(f"Status inquiry error: {str(e)}", exc_info=True)
            return False, {}, f"Error: {str(e)}"
