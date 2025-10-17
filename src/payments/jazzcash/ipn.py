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
                # Still return success acknowledgement to JazzCash
                return False, self._generate_acknowledgement_response(), "Missing transaction reference"

            # Get transaction
            try:
                transaction = JazzCashTransaction.objects.get(txn_ref_no=txn_ref_no)
            except JazzCashTransaction.DoesNotExist:
                logger.error(f"Transaction not found for IPN: {txn_ref_no}")
                # Still log the IPN
                self._log_ipn(None, txn_ref_no, txn_type, response_code, response_message,
                             ipn_data, secure_hash_received, '', False)
                # Still return success acknowledgement to JazzCash
                return False, self._generate_acknowledgement_response(), "Transaction not found"

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
                # Still return success acknowledgement to JazzCash
                return False, self._generate_acknowledgement_response(), "Security verification failed"

            # Update transaction based on IPN
            self._update_transaction(transaction, ipn_data, response_code)

            # Mark IPN as processed
            ipn_log.processed = True
            ipn_log.processed_at = timezone.now()
            ipn_log.save()

            # Return success acknowledgement
            logger.info(f"IPN processed successfully for {txn_ref_no}")
            return True, self._generate_acknowledgement_response(), "IPN processed successfully"

        except Exception as e:
            logger.error(f"IPN processing error: {str(e)}", exc_info=True)
            # Still return success acknowledgement to JazzCash
            return False, self._generate_acknowledgement_response(), f"Error: {str(e)}"

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

                        # Map transaction type to payment method
                        payment_method_map = {
                            'MWALLET': 'mwallet',
                            'MPAY': 'card',
                        }
                        payment_method = payment_method_map.get(transaction.txn_type, 'unknown')

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
                            payment_method=payment_method,
                            payment_amount=transaction.amount,
                            transaction_reference=transaction.txn_ref_no,
                            notes=f'Payment successful via IPN. Response: {ipn_data.get("pp_ResponseMessage", "")}'
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
                            payment_method=payment_method,
                            payment_amount=transaction.amount,
                            transaction_reference=transaction.txn_ref_no,
                            notes=f'Registration completed successfully with payment confirmation'
                        )

                        # Send registration success email
                        try:
                            from src.api.email_utils import send_registration_success_email

                            # Get selected workshops if any
                            workshops = transaction.registration.selected_workshops.all() if hasattr(transaction.registration, 'selected_workshops') else []

                            success, message = send_registration_success_email(
                                user=transaction.user,
                                event=transaction.event,
                                registration=transaction.registration,
                                transaction=transaction,
                                workshops=workshops
                            )

                            if success:
                                logger.info(f"Registration email sent to {transaction.user.email}")
                                # Log email sent
                                RegistrationLog.objects.create(
                                    event=transaction.event,
                                    user=transaction.user,
                                    registration=transaction.registration,
                                    action='email_sent',
                                    email=transaction.user.email,
                                    first_name=transaction.user.first_name,
                                    last_name=transaction.user.last_name,
                                    phone_number=transaction.user.phone_number if hasattr(transaction.user, 'phone_number') else '',
                                    registration_type=transaction.registration.registration_type,
                                    payment_method=payment_method,
                                    payment_amount=transaction.amount,
                                    transaction_reference=transaction.txn_ref_no,
                                    notes=f'Registration confirmation email sent successfully'
                                )
                            else:
                                logger.error(f"Failed to send registration email: {message}")
                                # Log email failed
                                RegistrationLog.objects.create(
                                    event=transaction.event,
                                    user=transaction.user,
                                    registration=transaction.registration,
                                    action='email_failed',
                                    email=transaction.user.email,
                                    first_name=transaction.user.first_name,
                                    last_name=transaction.user.last_name,
                                    phone_number=transaction.user.phone_number if hasattr(transaction.user, 'phone_number') else '',
                                    registration_type=transaction.registration.registration_type,
                                    payment_method=payment_method,
                                    payment_amount=transaction.amount,
                                    transaction_reference=transaction.txn_ref_no,
                                    notes=f'Failed to send registration email: {message}'
                                )
                        except Exception as e:
                            logger.error(f"Error sending registration email: {str(e)}", exc_info=True)
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

                # Log failed payment
                if transaction.event and transaction.registration:
                    # Map transaction type to payment method
                    payment_method_map = {
                        'MWALLET': 'mwallet',
                        'MPAY': 'card',
                    }
                    payment_method = payment_method_map.get(transaction.txn_type, 'unknown')

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
                        payment_method=payment_method,
                        payment_amount=transaction.amount,
                        transaction_reference=transaction.txn_ref_no,
                        notes=f'Payment failed via IPN. Response: {ipn_data.get("pp_ResponseMessage", "")} (Code: {response_code})'
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
                        payment_method=payment_method,
                        payment_amount=transaction.amount,
                        transaction_reference=transaction.txn_ref_no,
                        notes=f'Registration failed due to payment failure'
                    )

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

    def _generate_acknowledgement_response(self):
        """
        Generate acknowledgement response for JazzCash IPN

        According to JazzCash requirements, IPN must always return success acknowledgement
        to confirm receipt, regardless of internal processing status.

        Returns:
            dict: Acknowledgement response
        """
        ack_data = {
            'pp_ResponseCode': '000',
            'pp_ResponseMessage': 'Success',
        }

        # Generate secure hash for acknowledgement
        try:
            from .hmac_utils import generate_secure_hash
            ack_secure_hash = generate_secure_hash(ack_data, self.config.integrity_salt, include_empty=False)
        except Exception as e:
            logger.error(f"Error generating acknowledgement hash: {str(e)}")
            ack_secure_hash = ''

        return {
            'pp_ResponseCode': '000',
            'pp_ResponseMessage': 'Success',
            'pp_SecureHash': ack_secure_hash
        }
