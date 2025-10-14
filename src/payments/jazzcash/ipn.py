"""
JazzCash IPN (Instant Payment Notification) Handler
===================================================

Handle instant payment notifications from JazzCash
"""

import logging
from django.utils import timezone

from .config import jazzcash_config
from .hmac_utils import verify_secure_hash
from ..models import JazzCashTransaction, JazzCashIPNLog
from ..utils import is_successful_response

logger = logging.getLogger(__name__)


class IPNHandler:
    """
    Handler for JazzCash Instant Payment Notifications
    """

    def __init__(self):
        self.config = jazzcash_config

    def process_ipn(self, ipn_data):
        """
        Process IPN received from JazzCash

        Args:
            ipn_data (dict): IPN data from JazzCash

        Returns:
            tuple: (success: bool, response_data: dict, message: str)
        """
        try:
            logger.info(f"Processing IPN: {ipn_data}")

            # Extract key fields
            txn_ref_no = ipn_data.get('pp_TxnRefNo', '')
            txn_type = ipn_data.get('pp_TxnType', '')
            response_code = ipn_data.get('pp_ResponseCode', '')
            response_message = ipn_data.get('pp_ResponseMessage', '')
            secure_hash_received = ipn_data.get('pp_SecureHash', '')

            if not txn_ref_no:
                logger.error("IPN missing transaction reference")
                return False, self._generate_error_response(), "Missing transaction reference"

            # Get transaction
            try:
                transaction = JazzCashTransaction.objects.get(txn_ref_no=txn_ref_no)
            except JazzCashTransaction.DoesNotExist:
                logger.error(f"Transaction not found for IPN: {txn_ref_no}")
                # Still log the IPN
                self._log_ipn(None, txn_ref_no, txn_type, response_code, response_message,
                             ipn_data, secure_hash_received, '', False)
                return False, self._generate_error_response(), "Transaction not found"

            # Verify secure hash
            ipn_for_verification = {k: v for k, v in ipn_data.items() if k != 'pp_SecureHash'}
            secure_hash_calculated = ''
            is_verified = False

            try:
                from .hmac_utils import generate_secure_hash
                secure_hash_calculated = generate_secure_hash(ipn_for_verification, self.config.integrity_salt, include_empty=False)
                is_verified = secure_hash_calculated.upper() == secure_hash_received.upper()
            except Exception as e:
                logger.error(f"Error verifying IPN hash: {str(e)}")
                is_verified = False

            # Log IPN
            ipn_log = self._log_ipn(
                transaction, txn_ref_no, txn_type, response_code, response_message,
                ipn_data, secure_hash_received, secure_hash_calculated, is_verified
            )

            if not is_verified:
                logger.error(f"IPN hash verification failed for {txn_ref_no}")
                logger.error(f"Received:   {secure_hash_received}")
                logger.error(f"Calculated: {secure_hash_calculated}")
                return False, self._generate_error_response(), "Security verification failed"

            # Update transaction based on IPN
            self._update_transaction(transaction, ipn_data, response_code)

            # Mark IPN as processed
            ipn_log.processed = True
            ipn_log.processed_at = timezone.now()
            ipn_log.save()

            # Return success response
            success_response = {
                'pp_ResponseCode': '000',
                'pp_ResponseMessage': 'IPN received successfully',
                'pp_SecureHash': ''
            }

            logger.info(f"IPN processed successfully for {txn_ref_no}")
            return True, success_response, "IPN processed successfully"

        except Exception as e:
            logger.error(f"IPN processing error: {str(e)}", exc_info=True)
            return False, self._generate_error_response(), f"Error: {str(e)}"

    def _update_transaction(self, transaction, ipn_data, response_code):
        """
        Update transaction based on IPN data

        Args:
            transaction (JazzCashTransaction): Transaction object
            ipn_data (dict): IPN data
            response_code (str): Response code
        """
        # Update transaction with IPN data
        transaction.response_data = ipn_data
        transaction.pp_response_code = response_code
        transaction.pp_response_message = ipn_data.get('pp_ResponseMessage', '')
        transaction.pp_retrieval_ref_no = ipn_data.get('pp_RetreivalReferenceNo', '')
        transaction.pp_auth_code = ipn_data.get('pp_AuthCode', '')

        # Update status based on response code
        if is_successful_response(response_code):
            if transaction.status != 'completed':
                transaction.mark_completed(ipn_data)
                logger.info(f"Transaction {transaction.txn_ref_no} marked as completed via IPN")

                # Handle event registration
                if transaction.event:
                    if transaction.registration:
                        # Update existing registration
                        transaction.registration.status = 'confirmed'
                        transaction.registration.payment_status = 'paid'
                        transaction.registration.payment_amount = transaction.amount
                        transaction.registration.payment_date = timezone.now()
                        transaction.registration.save()
                        logger.info(f"Registration {transaction.registration.id} marked as paid")
                    else:
                        # Create new registration after successful payment
                        from src.api.models import Registration
                        registration = Registration.objects.create(
                            event=transaction.event,
                            user=transaction.user,
                            status='confirmed',
                            payment_status='paid',
                            payment_amount=transaction.amount,
                            payment_date=timezone.now()
                        )
                        transaction.registration = registration
                        transaction.save()
                        logger.info(f"Created new registration {registration.id} after successful payment")

                # Handle session registration
                if transaction.session:
                    if transaction.session_registration:
                        # Update existing session registration
                        transaction.session_registration.status = 'confirmed'
                        transaction.session_registration.payment_status = 'paid'
                        transaction.session_registration.payment_amount = transaction.amount
                        transaction.session_registration.payment_date = timezone.now()
                        transaction.session_registration.save()
                        logger.info(f"Session registration {transaction.session_registration.id} marked as paid")
                    else:
                        # Create new session registration after successful payment
                        from src.api.models import SessionRegistration
                        session_registration = SessionRegistration.objects.create(
                            session=transaction.session,
                            user=transaction.user,
                            status='confirmed',
                            payment_status='paid',
                            payment_amount=transaction.amount,
                            payment_date=timezone.now()
                        )
                        transaction.session_registration = session_registration
                        transaction.save()
                        logger.info(f"Created new session registration {session_registration.id} after successful payment")

        elif response_code in ['199', '999']:
            if transaction.status != 'failed':
                transaction.mark_failed(ipn_data)
                logger.info(f"Transaction {transaction.txn_ref_no} marked as failed via IPN")

        else:
            transaction.save()
            logger.info(f"Transaction {transaction.txn_ref_no} status unchanged: {response_code}")

    def _log_ipn(self, transaction, txn_ref_no, txn_type, response_code, response_message,
                 ipn_data, secure_hash_received, secure_hash_calculated, is_verified):
        """
        Log IPN to database

        Args:
            transaction (JazzCashTransaction or None): Transaction object
            txn_ref_no (str): Transaction reference number
            txn_type (str): Transaction type
            response_code (str): Response code
            response_message (str): Response message
            ipn_data (dict): Complete IPN data
            secure_hash_received (str): Received secure hash
            secure_hash_calculated (str): Calculated secure hash
            is_verified (bool): Whether hash is verified

        Returns:
            JazzCashIPNLog: Created log entry
        """
        # Check for duplicate IPN (retry)
        retry_count = JazzCashIPNLog.objects.filter(
            txn_ref_no=txn_ref_no,
            response_code=response_code
        ).count()

        ipn_log = JazzCashIPNLog.objects.create(
            transaction=transaction,
            txn_ref_no=txn_ref_no,
            txn_type=txn_type,
            response_code=response_code,
            response_message=response_message,
            ipn_data=ipn_data,
            secure_hash_received=secure_hash_received,
            secure_hash_calculated=secure_hash_calculated,
            is_verified=is_verified,
            retry_count=retry_count,
        )

        return ipn_log

    def _generate_error_response(self):
        """
        Generate error response for JazzCash

        Returns:
            dict: Error response
        """
        return {
            'pp_ResponseCode': '999',
            'pp_ResponseMessage': 'IPN processing failed',
            'pp_SecureHash': ''
        }
