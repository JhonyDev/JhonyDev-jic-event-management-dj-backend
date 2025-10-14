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
            print(f"\n{'='*80}")
            print(f"💳 PREPARING CARD PAYMENT FORM")
            print(f"{'='*80}")

            # Validate all objects before accessing their attributes
            print(f"📋 Validating input objects...")
            print(f"   - event: {event} (type: {type(event).__name__})")
            if event is None:
                print(f"   ❌ ERROR: event is None!")
                return False, {}, "Event object is None"
            else:
                print(f"   ✅ event.id: {event.id}")
                print(f"   ✅ event.title: {event.title}")

            print(f"   - user: {user} (type: {type(user).__name__})")
            if user is None:
                print(f"   ❌ ERROR: user is None!")
                return False, {}, "User object is None"
            else:
                print(f"   ✅ user.id: {user.id}")
                print(f"   ✅ user.username: {user.username}")

            print(f"   - session: {session} (type: {type(session).__name__ if session else 'NoneType'})")
            if session is not None:
                print(f"   ✅ session.id: {session.id}")
                print(f"   ✅ session.title: {session.title}")

            print(f"   - registration: {registration} (type: {type(registration).__name__ if registration else 'NoneType'})")
            if registration is not None:
                print(f"   ✅ registration.id: {registration.id}")

            print(f"   - session_registration: {session_registration} (type: {type(session_registration).__name__ if session_registration else 'NoneType'})")
            if session_registration is not None:
                print(f"   ✅ session_registration.id: {session_registration.id}")

            print(f"\n💰 Payment Details:")
            print(f"   - Amount: {amount} PKR")
            print(f"{'='*80}\n")

            # Generate transaction details
            print(f"📋 Generating transaction details...")
            txn_ref_no = generate_txn_ref_no()
            print(f"  ✅ Transaction Ref: {txn_ref_no}")

            print(f"  📋 Calling generate_bill_reference(event.id={event.id}, user.id={user.id})")
            try:
                bill_reference = generate_bill_reference(event.id, user.id)
                print(f"  ✅ Bill Reference: {bill_reference}")
            except Exception as e:
                print(f"  ❌ ERROR in generate_bill_reference: {type(e).__name__}: {str(e)}")
                raise

            amount_in_paisa = amount_to_paisa(amount)
            print(f"  ✅ Amount in Paisa: {amount_in_paisa}")

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
            print(f"\n💾 Creating transaction record in database...")
            print(f"  📋 Transaction data:")
            print(f"     - event: {event} (id: {event.id if event else 'N/A'})")
            print(f"     - user: {user} (id: {user.id if user else 'N/A'})")
            print(f"     - registration: {registration} (id: {registration.id if registration else 'N/A'})")
            print(f"     - session: {session} (id: {session.id if session else 'N/A'})")
            print(f"     - session_registration: {session_registration} (id: {session_registration.id if session_registration else 'N/A'})")
            print(f"     - txn_ref_no: {txn_ref_no}")
            print(f"     - amount: {amount}")

            try:
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
                print(f"  ✅ Transaction saved (DB ID: {transaction.id}, Status: pending)\n")
            except Exception as e:
                print(f"  ❌ ERROR creating transaction: {type(e).__name__}: {str(e)}")
                import traceback
                print(f"  Traceback:")
                print(traceback.format_exc())
                raise

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
                        from django.utils import timezone
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
