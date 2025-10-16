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
            print(f"\n{'='*80}")
            print(f"📥 HANDLING CARD PAYMENT RETURN RESPONSE")
            print(f"{'='*80}")
            print(f"Response data received:")
            for key, value in response_data.items():
                print(f"   {key}: {value}")
            print(f"{'='*80}\n")

            txn_ref_no = response_data.get('pp_TxnRefNo', '')
            print(f"📋 Step 1: Extracting transaction reference...")
            print(f"   TxnRefNo: {txn_ref_no}")

            if not txn_ref_no:
                print(f"   ❌ ERROR: No transaction reference in response")
                logger.error("No transaction reference in response")
                return False, None, "Invalid response: No transaction reference"
            print(f"   ✅ Transaction reference found\n")

            # Get transaction
            print(f"📋 Step 2: Looking up transaction in database...")
            try:
                transaction = JazzCashTransaction.objects.get(txn_ref_no=txn_ref_no)
                print(f"   ✅ Transaction found: ID {transaction.id}")
                print(f"      - User: {transaction.user.username}")
                print(f"      - Amount: {transaction.amount} PKR")
                print(f"      - Current Status: {transaction.status}")
            except JazzCashTransaction.DoesNotExist:
                print(f"   ❌ ERROR: Transaction not found in database")
                logger.error(f"Transaction not found: {txn_ref_no}")
                return False, None, "Transaction not found"
            print()

            # Verify secure hash
            print(f"📋 Step 3: Verifying security hash...")
            received_hash = response_data.get('pp_SecureHash', '')
            print(f"   Received Hash: {received_hash}")

            response_for_verification = {k: v for k, v in response_data.items() if k != 'pp_SecureHash'}
            print(f"   Fields to verify: {len(response_for_verification)}")
            print(f"   Calling verify_secure_hash()...")

            is_verified = verify_secure_hash(response_for_verification, received_hash, self.config.integrity_salt)

            if not is_verified:
                print(f"   ❌ HASH VERIFICATION FAILED!")
                logger.error(f"Hash verification failed for transaction {txn_ref_no}")
                transaction.status = 'failed'
                transaction.response_data = response_data
                transaction.save()
                print(f"   Transaction marked as failed")
                return False, transaction, "Security verification failed"
            print(f"   ✅ Hash verified successfully\n")

            # Update transaction with response
            print(f"📋 Step 4: Updating transaction with response data...")
            transaction.response_data = response_data
            transaction.pp_response_code = response_data.get('pp_ResponseCode', '')
            transaction.pp_response_message = response_data.get('pp_ResponseMessage', '')
            transaction.pp_retrieval_ref_no = response_data.get('pp_RetreivalReferenceNo', '')
            transaction.pp_auth_code = response_data.get('pp_AuthCode', '')
            transaction.pp_version = response_data.get('pp_Version', '')
            transaction.pp_txn_type = response_data.get('pp_TxnType', '')
            print(f"   Response Code: {transaction.pp_response_code}")
            print(f"   Response Message: {transaction.pp_response_message}")
            print(f"   ✅ Transaction updated\n")

            # Check response code
            print(f"📋 Step 5: Checking payment status...")
            response_code = response_data.get('pp_ResponseCode', '')
            print(f"   Response Code: {response_code}")
            print(f"   Calling is_successful_response({response_code})...")

            if is_successful_response(response_code):
                print(f"   ✅ Payment is SUCCESSFUL!")
                transaction.mark_completed(response_data)
                print(f"   ✅ Transaction marked as completed")
                logger.info(f"Card payment successful: {txn_ref_no}")

                # Handle event registration (only if this is an event payment, not a session payment)
                if transaction.event and not transaction.session:
                    print(f"\n  📌 Processing EVENT registration...")
                    print(f"     Event ID: {transaction.event.id}")
                    print(f"     Event Title: {transaction.event.title}")

                    if transaction.registration:
                        print(f"     Existing registration found (linked to transaction): ID {transaction.registration.id}")
                        print(f"     Updating existing registration...")
                        # Update existing registration
                        from django.utils import timezone
                        transaction.registration.status = 'confirmed'
                        transaction.registration.payment_status = 'paid'
                        transaction.registration.payment_amount = transaction.amount
                        transaction.registration.payment_date = timezone.now()
                        transaction.registration.save()
                        logger.info(f"Registration {transaction.registration.id} marked as paid")
                        print(f"     ✅ Registration {transaction.registration.id} updated to PAID")

                        # Send registration success email
                        try:
                            from src.api.email_utils import send_registration_success_email
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
                                print(f"     📧 Registration confirmation email sent to {transaction.user.email}")
                            else:
                                logger.error(f"Failed to send registration email: {message}")
                                print(f"     ❌ Failed to send email: {message}")
                        except Exception as e:
                            logger.error(f"Error sending registration email: {str(e)}", exc_info=True)
                            print(f"     ❌ Email error: {str(e)}")
                    else:
                        # Check if registration already exists in database
                        from src.api.models import Registration
                        from django.utils import timezone
                        print(f"     No registration linked to transaction")
                        print(f"     Checking if registration exists in database...")

                        existing_reg = Registration.objects.filter(
                            event=transaction.event,
                            user=transaction.user
                        ).first()

                        if existing_reg:
                            print(f"     ✅ Found existing registration in DB: ID {existing_reg.id}")
                            print(f"     Updating existing registration...")
                            existing_reg.status = 'confirmed'
                            existing_reg.payment_status = 'paid'
                            existing_reg.payment_amount = transaction.amount
                            existing_reg.payment_date = timezone.now()
                            existing_reg.save()
                            transaction.registration = existing_reg
                            transaction.save()
                            logger.info(f"Updated existing registration {existing_reg.id}")
                            print(f"     ✅ Registration {existing_reg.id} updated to PAID")

                            # Send registration success email
                            try:
                                from src.api.email_utils import send_registration_success_email
                                workshops = existing_reg.selected_workshops.all() if hasattr(existing_reg, 'selected_workshops') else []

                                success, message = send_registration_success_email(
                                    user=transaction.user,
                                    event=transaction.event,
                                    registration=existing_reg,
                                    transaction=transaction,
                                    workshops=workshops
                                )

                                if success:
                                    logger.info(f"Registration email sent to {transaction.user.email}")
                                    print(f"     📧 Registration confirmation email sent to {transaction.user.email}")
                                else:
                                    logger.error(f"Failed to send registration email: {message}")
                                    print(f"     ❌ Failed to send email: {message}")
                            except Exception as e:
                                logger.error(f"Error sending registration email: {str(e)}", exc_info=True)
                                print(f"     ❌ Email error: {str(e)}")
                        else:
                            print(f"     No existing registration found, creating new one...")
                            # Create new registration after successful payment
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
                            print(f"     ✅ NEW registration created: ID {registration.id}")

                            # Send registration success email
                            try:
                                from src.api.email_utils import send_registration_success_email
                                workshops = registration.selected_workshops.all() if hasattr(registration, 'selected_workshops') else []

                                success, message = send_registration_success_email(
                                    user=transaction.user,
                                    event=transaction.event,
                                    registration=registration,
                                    transaction=transaction,
                                    workshops=workshops
                                )

                                if success:
                                    logger.info(f"Registration email sent to {transaction.user.email}")
                                    print(f"     📧 Registration confirmation email sent to {transaction.user.email}")
                                else:
                                    logger.error(f"Failed to send registration email: {message}")
                                    print(f"     ❌ Failed to send email: {message}")
                            except Exception as e:
                                logger.error(f"Error sending registration email: {str(e)}", exc_info=True)
                                print(f"     ❌ Email error: {str(e)}")

                # Handle session registration
                if transaction.session:
                    print(f"\n  📌 Processing SESSION registration...")
                    print(f"     Session ID: {transaction.session.id}")
                    print(f"     Session Title: {transaction.session.title}")
                    print(f"     User ID: {transaction.user.id}")
                    print(f"     User: {transaction.user.username}")

                    if transaction.session_registration:
                        print(f"     Existing session_registration found (linked to transaction): ID {transaction.session_registration.id}")
                        print(f"     Updating existing session registration...")
                        # Update existing session registration
                        from django.utils import timezone
                        transaction.session_registration.status = 'confirmed'
                        transaction.session_registration.payment_status = 'paid'
                        transaction.session_registration.payment_amount = transaction.amount
                        transaction.session_registration.payment_date = timezone.now()
                        transaction.session_registration.save()
                        logger.info(f"Session registration {transaction.session_registration.id} marked as paid")
                        print(f"     ✅ Session registration {transaction.session_registration.id} updated to PAID")
                    else:
                        # Check if session registration already exists in database
                        from src.api.models import SessionRegistration
                        from django.utils import timezone
                        print(f"     No session_registration linked to transaction")
                        print(f"     Checking if session registration exists in database...")

                        existing_session_reg = SessionRegistration.objects.filter(
                            session=transaction.session,
                            user=transaction.user
                        ).first()

                        if existing_session_reg:
                            print(f"     ✅ Found existing session registration in DB: ID {existing_session_reg.id}")
                            print(f"     Updating existing session registration...")
                            existing_session_reg.status = 'confirmed'
                            existing_session_reg.payment_status = 'paid'
                            existing_session_reg.payment_amount = transaction.amount
                            existing_session_reg.payment_date = timezone.now()
                            existing_session_reg.save()
                            transaction.session_registration = existing_session_reg
                            transaction.save()
                            logger.info(f"Updated existing session registration {existing_session_reg.id}")
                            print(f"     ✅ Session registration {existing_session_reg.id} updated to PAID")
                        else:
                            print(f"     No existing session registration found, creating new one...")
                            # Create new session registration after successful payment
                            try:
                                session_registration = SessionRegistration.objects.create(
                                    session=transaction.session,
                                    user=transaction.user,
                                    status='confirmed',
                                    payment_status='paid',
                                    payment_amount=transaction.amount,
                                    payment_date=timezone.now()
                                )
                                print(f"     ✅ NEW session registration created! ID: {session_registration.id}")
                                print(f"        - Session: {session_registration.session.title} (ID: {session_registration.session.id})")
                                print(f"        - User: {session_registration.user.username} (ID: {session_registration.user.id})")
                                print(f"        - Status: {session_registration.status}")
                                print(f"        - Payment Status: {session_registration.payment_status}")
                                print(f"        - Payment Amount: {session_registration.payment_amount}")

                                transaction.session_registration = session_registration
                                transaction.save()
                                print(f"     ✅ Transaction updated with session_registration link")

                                logger.info(f"Created new session registration {session_registration.id} after successful payment")
                            except Exception as e:
                                print(f"     ❌ ERROR creating session registration: {type(e).__name__}: {str(e)}")
                                import traceback
                                print(traceback.format_exc())
                else:
                    if transaction.event and not transaction.session:
                        print(f"\n  ℹ️  This is an EVENT payment (no session involved)")
                    else:
                        print(f"\n  ⚠️  Warning: No session or event associated with this transaction")

                print(f"\n{'='*80}")
                print(f"✅ PAYMENT SUCCESSFUL!")
                print(f"   Transaction: {txn_ref_no}")
                print(f"   Amount: {transaction.amount} PKR")
                print(f"   Status: completed")
                print(f"{'='*80}\n")
                print(f"📤 Returning to view: success=True, message='Payment successful'")
                return True, transaction, "Payment successful"
            else:
                print(f"   ❌ Payment FAILED!")
                print(f"   Reason: {response_data.get('pp_ResponseMessage', 'Unknown')}")
                transaction.mark_failed(response_data)
                print(f"   ✅ Transaction marked as failed")
                logger.warning(f"Card payment failed: {txn_ref_no} - {response_data.get('pp_ResponseMessage')}")

                print(f"\n{'='*80}")
                print(f"❌ PAYMENT FAILED!")
                print(f"   Transaction: {txn_ref_no}")
                print(f"   Reason: {response_data.get('pp_ResponseMessage', 'Payment failed')}")
                print(f"{'='*80}\n")
                print(f"📤 Returning to view: success=False, message='{response_data.get('pp_ResponseMessage', 'Payment failed')}'")
                return False, transaction, response_data.get('pp_ResponseMessage', 'Payment failed')

        except Exception as e:
            print(f"\n❌ EXCEPTION in handle_return_response!")
            print(f"   Error: {str(e)}")
            import traceback
            print(traceback.format_exc())
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
