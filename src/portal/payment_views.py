"""
Anonymous Payment Views for Self-Registration
==============================================

These views handle payment processing for anonymous users during self-registration.
They are separate from the existing payment system to avoid modifying authenticated flows.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from decimal import Decimal, InvalidOperation
import json
import logging

from src.api.models import Event, Registration, Session, EventRegistrationType, RegistrationLog
from src.payments.jazzcash.mwallet import MWalletClient
from src.payments.jazzcash.card import CardPaymentHandler
from src.payments.models import JazzCashTransaction

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Helper function to get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@csrf_exempt
@require_http_methods(["POST"])
def anonymous_mwallet_payment(request, event_pk):
    """
    Handle MWallet payment for anonymous self-registration

    POST /portal/register/<event_pk>/payment/mwallet/
    """
    try:
        event = get_object_or_404(Event, pk=event_pk, status='published')

        # Parse JSON request body
        data = json.loads(request.body)

        amount = Decimal(str(data.get('amount')))
        mobile_number = data.get('mobile_number')
        cnic = data.get('cnic')
        registration_data = data.get('registration_data', {})

        # Validate required fields
        if not amount or not mobile_number or not cnic:
            return JsonResponse({
                'success': False,
                'error': 'Missing required payment fields'
            }, status=400)

        # Create or get user from registration data
        from django.contrib.auth import get_user_model
        User = get_user_model()

        email = registration_data.get('email')
        if not email:
            return JsonResponse({
                'success': False,
                'error': 'Email is required'
            }, status=400)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'first_name': registration_data.get('first_name', ''),
                'last_name': registration_data.get('last_name', ''),
                'phone_number': registration_data.get('phone_number', ''),
                'designation': registration_data.get('designation', ''),
                'affiliations': registration_data.get('affiliations', ''),
                'address': registration_data.get('address', ''),
                'country': registration_data.get('country', ''),
            }
        )

        # Update user info if already exists
        if not created:
            user.first_name = registration_data.get('first_name', user.first_name)
            user.last_name = registration_data.get('last_name', user.last_name)
            user.phone_number = registration_data.get('phone_number', user.phone_number)
            if registration_data.get('designation'):
                user.designation = registration_data.get('designation')
            if registration_data.get('affiliations'):
                user.affiliations = registration_data.get('affiliations')
            if registration_data.get('address'):
                user.address = registration_data.get('address')
            if registration_data.get('country'):
                user.country = registration_data.get('country')
            user.save()

        # Check if already registered
        existing_registration = Registration.objects.filter(event=event, user=user).first()

        # Get registration type if provided
        registration_type = None
        registration_type_id = registration_data.get('registration_type')
        if registration_type_id:
            try:
                registration_type = EventRegistrationType.objects.get(
                    id=registration_type_id,
                    event=event
                )
            except EventRegistrationType.DoesNotExist:
                pass

        # Create pending registration (will be confirmed after payment)
        if not existing_registration:
            registration = Registration.objects.create(
                event=event,
                user=user,
                status='pending',  # Will be updated to 'confirmed' after successful payment
                payment_status='pending',
                registration_type=registration_type,
                designation=registration_data.get('designation', ''),
                affiliations=registration_data.get('affiliations', ''),
                address=registration_data.get('address', ''),
                country=registration_data.get('country', ''),
                phone_number=registration_data.get('phone_number', ''),
            )

            # Add selected workshops
            workshop_ids = registration_data.get('workshops', [])
            if workshop_ids:
                # Ensure workshop_ids is a list
                if isinstance(workshop_ids, str):
                    try:
                        workshop_ids = json.loads(workshop_ids)
                    except (json.JSONDecodeError, ValueError):
                        # If it's a comma-separated string
                        workshop_ids = [int(id.strip()) for id in workshop_ids.split(',') if id.strip().isdigit()]
                elif isinstance(workshop_ids, int):
                    workshop_ids = [workshop_ids]
                elif not isinstance(workshop_ids, list):
                    # Try to convert iterable to list, otherwise wrap in list
                    try:
                        workshop_ids = list(workshop_ids)
                    except TypeError:
                        workshop_ids = [workshop_ids]

                workshops = Session.objects.filter(
                    id__in=workshop_ids,
                    agenda__event=event,
                    session_type='workshop'
                )
                registration.selected_workshops.set(workshops)
        else:
            registration = existing_registration

        # Log payment initiation
        RegistrationLog.objects.create(
            event=event,
            user=user,
            registration=registration,
            action='payment_method_selected',
            email=email,
            first_name=registration_data.get('first_name', ''),
            last_name=registration_data.get('last_name', ''),
            phone_number=registration_data.get('phone_number', ''),
            registration_type=registration_type,
            payment_method='mwallet',
            payment_amount=amount,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            notes='User selected JazzCash Mobile Wallet payment method'
        )

        # Initiate MWallet payment
        client = MWalletClient()
        success, response_data, message = client.initiate_payment(
            event=event,
            user=user,
            amount=amount,
            mobile_number=mobile_number,
            cnic=cnic,
            description=f'Registration payment for {event.title}',
            registration=registration
        )

        if success:
            # Log payment request sent to JazzCash
            RegistrationLog.objects.create(
                event=event,
                user=user,
                registration=registration,
                action='payment_initiated',
                email=email,
                first_name=registration_data.get('first_name', ''),
                last_name=registration_data.get('last_name', ''),
                phone_number=registration_data.get('phone_number', ''),
                registration_type=registration_type,
                payment_method='mwallet',
                payment_amount=amount,
                transaction_reference=response_data.get('pp_TxnRefNo', ''),
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                notes=f'MWallet payment request sent to JazzCash. {message}'
            )

            return JsonResponse({
                'success': True,
                'message': message,
                'txn_ref_no': response_data.get('pp_TxnRefNo'),
            })
        else:
            # Log failed payment initiation
            RegistrationLog.objects.create(
                event=event,
                user=user,
                registration=registration,
                action='payment_failed',
                email=email,
                first_name=registration_data.get('first_name', ''),
                last_name=registration_data.get('last_name', ''),
                phone_number=registration_data.get('phone_number', ''),
                registration_type=registration_type,
                payment_method='mwallet',
                payment_amount=amount,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                notes=f'MWallet payment initiation failed: {message}'
            )

            # Delete pending registration if payment initiation failed
            if registration.status == 'pending':
                registration.delete()

            return JsonResponse({
                'success': False,
                'error': message
            }, status=400)

    except Exception as e:
        logger.error(f"Anonymous MWallet payment error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Payment error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def anonymous_card_payment(request, event_pk):
    """
    Handle Card payment for anonymous self-registration

    POST /portal/register/<event_pk>/payment/card/
    """
    try:
        print(f"\n{'='*80}")
        print(f"🔷 ANONYMOUS CARD PAYMENT REQUEST")
        print(f"{'='*80}")
        print(f"Event PK: {event_pk}")
        print(f"Request body raw: {request.body[:500]}")  # First 500 chars

        event = get_object_or_404(Event, pk=event_pk, status='published')

        # Parse JSON request body
        try:
            data = json.loads(request.body)
            print(f"✅ JSON parsed successfully")
            print(f"Data keys: {list(data.keys())}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Invalid JSON: {str(e)}'
            }, status=400)

        amount = data.get('amount')
        print(f"Amount from request: {amount} (type: {type(amount)})")

        registration_data = data.get('registration_data', {})
        print(f"Registration data keys: {list(registration_data.keys())}")
        print(f"Registration data: {registration_data}")

        # Convert amount to Decimal
        try:
            amount = Decimal(str(amount))
            print(f"Amount converted to Decimal: {amount}")
        except (ValueError, TypeError, InvalidOperation) as e:
            print(f"❌ Amount conversion error: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Invalid amount: {str(e)}'
            }, status=400)

        # Validate required fields
        if not amount:
            return JsonResponse({
                'success': False,
                'error': 'Amount is required'
            }, status=400)

        # Create or get user from registration data
        from django.contrib.auth import get_user_model
        User = get_user_model()

        email = registration_data.get('email')
        if not email:
            return JsonResponse({
                'success': False,
                'error': 'Email is required'
            }, status=400)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'first_name': registration_data.get('first_name', ''),
                'last_name': registration_data.get('last_name', ''),
                'phone_number': registration_data.get('phone_number', ''),
                'designation': registration_data.get('designation', ''),
                'affiliations': registration_data.get('affiliations', ''),
                'address': registration_data.get('address', ''),
                'country': registration_data.get('country', ''),
            }
        )

        # Update user info if already exists
        if not created:
            user.first_name = registration_data.get('first_name', user.first_name)
            user.last_name = registration_data.get('last_name', user.last_name)
            user.phone_number = registration_data.get('phone_number', user.phone_number)
            if registration_data.get('designation'):
                user.designation = registration_data.get('designation')
            if registration_data.get('affiliations'):
                user.affiliations = registration_data.get('affiliations')
            if registration_data.get('address'):
                user.address = registration_data.get('address')
            if registration_data.get('country'):
                user.country = registration_data.get('country')
            user.save()

        # Check if already registered
        existing_registration = Registration.objects.filter(event=event, user=user).first()

        # Get registration type if provided
        registration_type = None
        registration_type_id = registration_data.get('registration_type')
        if registration_type_id:
            try:
                registration_type = EventRegistrationType.objects.get(
                    id=registration_type_id,
                    event=event
                )
            except EventRegistrationType.DoesNotExist:
                pass

        # Create pending registration (will be confirmed after payment)
        if not existing_registration:
            registration = Registration.objects.create(
                event=event,
                user=user,
                status='pending',  # Will be updated to 'confirmed' after successful payment
                payment_status='pending',
                registration_type=registration_type,
                designation=registration_data.get('designation', ''),
                affiliations=registration_data.get('affiliations', ''),
                address=registration_data.get('address', ''),
                country=registration_data.get('country', ''),
                phone_number=registration_data.get('phone_number', ''),
            )

            # Add selected workshops
            workshop_ids = registration_data.get('workshops', [])
            if workshop_ids:
                # Ensure workshop_ids is a list
                if isinstance(workshop_ids, str):
                    try:
                        workshop_ids = json.loads(workshop_ids)
                    except (json.JSONDecodeError, ValueError):
                        # If it's a comma-separated string
                        workshop_ids = [int(id.strip()) for id in workshop_ids.split(',') if id.strip().isdigit()]
                elif isinstance(workshop_ids, int):
                    workshop_ids = [workshop_ids]
                elif not isinstance(workshop_ids, list):
                    # Try to convert iterable to list, otherwise wrap in list
                    try:
                        workshop_ids = list(workshop_ids)
                    except TypeError:
                        workshop_ids = [workshop_ids]

                workshops = Session.objects.filter(
                    id__in=workshop_ids,
                    agenda__event=event,
                    session_type='workshop'
                )
                registration.selected_workshops.set(workshops)
        else:
            registration = existing_registration

        # Log payment method selection and initiation
        RegistrationLog.objects.create(
            event=event,
            user=user,
            registration=registration,
            action='payment_method_selected',
            email=email,
            first_name=registration_data.get('first_name', ''),
            last_name=registration_data.get('last_name', ''),
            phone_number=registration_data.get('phone_number', ''),
            registration_type=registration_type,
            payment_method='card',
            payment_amount=amount,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            notes='User selected Debit/Credit Card payment method'
        )

        # Prepare card payment form
        handler = CardPaymentHandler()
        success, form_data, message = handler.prepare_payment_form(
            event=event,
            user=user,
            amount=amount,
            description=f'Registration payment for {event.title}',
            registration=registration
        )

        if success:
            # Log payment form ready
            RegistrationLog.objects.create(
                event=event,
                user=user,
                registration=registration,
                action='payment_initiated',
                email=email,
                first_name=registration_data.get('first_name', ''),
                last_name=registration_data.get('last_name', ''),
                phone_number=registration_data.get('phone_number', ''),
                registration_type=registration_type,
                payment_method='card',
                payment_amount=amount,
                transaction_reference=form_data.get('txn_ref_no', ''),
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                notes=f'Card payment form prepared and ready for user submission. {message}'
            )

            return JsonResponse({
                'success': True,
                'form_data': form_data,
                'message': 'Payment form prepared',
            })
        else:
            # Log failed payment form preparation
            RegistrationLog.objects.create(
                event=event,
                user=user,
                registration=registration,
                action='payment_failed',
                email=email,
                first_name=registration_data.get('first_name', ''),
                last_name=registration_data.get('last_name', ''),
                phone_number=registration_data.get('phone_number', ''),
                registration_type=registration_type,
                payment_method='card',
                payment_amount=amount,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                notes=f'Card payment form preparation failed: {message}'
            )

            # Delete pending registration if payment form preparation failed
            if registration.status == 'pending':
                registration.delete()

            return JsonResponse({
                'success': False,
                'error': message
            }, status=400)

    except Exception as e:
        logger.error(f"Anonymous Card payment error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Payment error: {str(e)}'
        }, status=500)


def payment_status_view(request, event_pk, txn_ref_no):
    """
    Display payment status page

    GET /portal/register/<event_pk>/payment/status/<txn_ref_no>/
    """
    try:
        event = get_object_or_404(Event, pk=event_pk)
        transaction = get_object_or_404(JazzCashTransaction, txn_ref_no=txn_ref_no)

        context = {
            'event': event,
            'transaction': transaction,
        }

        return render(request, 'portal/events/payment_status.html', context)

    except Exception as e:
        logger.error(f"Payment status view error: {str(e)}", exc_info=True)
        return render(request, 'portal/events/payment_status.html', {
            'error': 'Transaction not found'
        })


@require_http_methods(["GET"])
def check_payment_status(request, event_pk, txn_ref_no):
    """
    Check payment status (for polling)

    GET /portal/register/<event_pk>/payment/status/check/<txn_ref_no>/
    """
    try:
        transaction = get_object_or_404(JazzCashTransaction, txn_ref_no=txn_ref_no)

        return JsonResponse({
            'success': True,
            'status': transaction.status,  # pending, completed, failed
            'message': transaction.pp_response_message or '',
            'amount': str(transaction.amount),
            'txn_ref_no': transaction.txn_ref_no,
        })

    except JazzCashTransaction.DoesNotExist:
        return JsonResponse({
            'success': False,
            'status': 'not_found',
            'message': 'Transaction not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Check payment status error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def log_payment_success_view(request, event_pk, txn_ref_no):
    """
    Log when user views the payment success page

    POST /portal/register/<event_pk>/log/payment-success/<txn_ref_no>/
    """
    try:
        event = get_object_or_404(Event, pk=event_pk)
        transaction = get_object_or_404(JazzCashTransaction, txn_ref_no=txn_ref_no)

        # Only log if transaction is completed and has a registration
        if transaction.status == 'completed' and transaction.registration:
            # Check if we haven't logged this already
            existing_log = RegistrationLog.objects.filter(
                transaction_reference=txn_ref_no,
                action='payment_success_viewed'
            ).first()

            if not existing_log:
                RegistrationLog.objects.create(
                    event=event,
                    user=transaction.user,
                    registration=transaction.registration,
                    action='payment_success_viewed',
                    email=transaction.user.email,
                    first_name=transaction.user.first_name,
                    last_name=transaction.user.last_name,
                    phone_number=transaction.user.phone_number if hasattr(transaction.user, 'phone_number') else '',
                    registration_type=transaction.registration.registration_type,
                    payment_method=transaction.payment_method,
                    payment_amount=transaction.amount,
                    transaction_reference=txn_ref_no,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                    notes=f'User viewed payment success page for transaction {txn_ref_no}'
                )

        return JsonResponse({'success': True})

    except Exception as e:
        logger.error(f"Log payment success view error: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def anonymous_bank_transfer(request, event_pk):
    """
    Handle Bank Transfer payment for anonymous self-registration

    POST /portal/register/<event_pk>/payment/bank/
    """
    try:
        event = get_object_or_404(Event, pk=event_pk, status='published')

        # Get form data
        amount = Decimal(str(request.POST.get('amount')))
        payment_date = request.POST.get('payment_date')
        receipt_image = request.FILES.get('receipt_image')
        notes = request.POST.get('notes', '')

        # Validate required fields
        if not amount or not payment_date or not receipt_image:
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)

        # Parse registration data (comes as registration_data[key])
        registration_data = {}
        for key, value in request.POST.items():
            if key.startswith('registration_data[') and key.endswith(']'):
                field_name = key[18:-1]  # Extract field name from registration_data[field_name]
                registration_data[field_name] = value

        # Create or get user from registration data
        from django.contrib.auth import get_user_model
        User = get_user_model()

        email = registration_data.get('email')
        if not email:
            return JsonResponse({
                'success': False,
                'error': 'Email is required'
            }, status=400)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'first_name': registration_data.get('first_name', ''),
                'last_name': registration_data.get('last_name', ''),
                'phone_number': registration_data.get('phone_number', ''),
                'designation': registration_data.get('designation', ''),
                'affiliations': registration_data.get('affiliations', ''),
                'address': registration_data.get('address', ''),
                'country': registration_data.get('country', ''),
            }
        )

        # Update user info if already exists
        if not created:
            user.first_name = registration_data.get('first_name', user.first_name)
            user.last_name = registration_data.get('last_name', user.last_name)
            user.phone_number = registration_data.get('phone_number', user.phone_number)
            if registration_data.get('designation'):
                user.designation = registration_data.get('designation')
            if registration_data.get('affiliations'):
                user.affiliations = registration_data.get('affiliations')
            if registration_data.get('address'):
                user.address = registration_data.get('address')
            if registration_data.get('country'):
                user.country = registration_data.get('country')
            user.save()

        # Check if already registered
        existing_registration = Registration.objects.filter(event=event, user=user).first()

        # Get registration type if provided
        registration_type = None
        registration_type_id = registration_data.get('registration_type')
        if registration_type_id:
            try:
                registration_type = EventRegistrationType.objects.get(
                    id=registration_type_id,
                    event=event
                )
            except EventRegistrationType.DoesNotExist:
                pass

        # Create pending registration (will be confirmed after organizer approval)
        if not existing_registration:
            registration = Registration.objects.create(
                event=event,
                user=user,
                status='pending',  # Will be updated to 'confirmed' after organizer approves
                payment_status='pending',
                registration_type=registration_type,
                designation=registration_data.get('designation', ''),
                affiliations=registration_data.get('affiliations', ''),
                address=registration_data.get('address', ''),
                country=registration_data.get('country', ''),
                phone_number=registration_data.get('phone_number', ''),
            )

            # Add selected workshops
            workshop_ids = registration_data.get('workshops', '')
            if workshop_ids:
                # Handle multiple workshops (comma-separated or array)
                if isinstance(workshop_ids, str):
                    if workshop_ids.strip():
                        workshop_ids = [int(id.strip()) for id in workshop_ids.split(',') if id.strip().isdigit()]
                    else:
                        workshop_ids = []
                elif isinstance(workshop_ids, int):
                    workshop_ids = [workshop_ids]
                elif isinstance(workshop_ids, list):
                    pass  # Already a list
                else:
                    # Try to convert to list
                    try:
                        workshop_ids = list(workshop_ids)
                    except TypeError:
                        workshop_ids = [workshop_ids]

                if workshop_ids:
                    workshops = Session.objects.filter(
                        id__in=workshop_ids,
                        agenda__event=event,
                        session_type='workshop'
                    )
                    registration.selected_workshops.set(workshops)
        else:
            registration = existing_registration

        # Log payment method selection
        RegistrationLog.objects.create(
            event=event,
            user=user,
            registration=registration,
            action='payment_method_selected',
            email=email,
            first_name=registration_data.get('first_name', ''),
            last_name=registration_data.get('last_name', ''),
            phone_number=registration_data.get('phone_number', ''),
            registration_type=registration_type,
            payment_method='bank',
            payment_amount=amount,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            notes='User selected Offline Bank Transfer payment method'
        )

        # Create bank payment receipt
        from src.api.models import BankPaymentReceipt
        from datetime import datetime

        receipt = BankPaymentReceipt.objects.create(
            event=event,
            user=user,
            registration=registration,
            registration_type=registration_type,
            receipt_image=receipt_image,
            amount=amount,
            transaction_id='',  # No transaction ID required
            payment_date=datetime.strptime(payment_date, '%Y-%m-%d').date(),
            notes=notes,
            status='pending'
        )

        # Log payment initiated (pending approval)
        RegistrationLog.objects.create(
            event=event,
            user=user,
            registration=registration,
            action='payment_initiated',
            email=email,
            first_name=registration_data.get('first_name', ''),
            last_name=registration_data.get('last_name', ''),
            phone_number=registration_data.get('phone_number', ''),
            registration_type=registration_type,
            payment_method='bank',
            payment_amount=amount,
            transaction_reference=f'bank_receipt_{receipt.id}',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            notes=f'Bank transfer receipt uploaded (Receipt ID: {receipt.id}). Pending organizer approval.'
        )

        return JsonResponse({
            'success': True,
            'message': 'Registration submitted successfully! Pending organizer approval.',
            'receipt_id': receipt.id
        })

    except Exception as e:
        logger.error(f"Anonymous Bank Transfer error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Submission error: {str(e)}'
        }, status=500)
