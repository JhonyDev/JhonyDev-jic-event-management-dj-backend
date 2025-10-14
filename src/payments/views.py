"""
API Views for JazzCash Payments
"""

from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
import logging

from src.api.models import Event, Registration, Session, SessionRegistration
from .models import JazzCashTransaction, JazzCashRefund
from .serializers import (
    JazzCashTransactionSerializer,
    JazzCashRefundSerializer,
    MWalletPaymentRequestSerializer,
    CardPaymentRequestSerializer,
    RefundRequestSerializer,
    StatusInquiryRequestSerializer,
)
from .jazzcash.mwallet import MWalletClient
from .jazzcash.card import CardPaymentHandler
from .jazzcash.ipn import IPNHandler
from .jazzcash.inquiry import StatusInquiryClient
from .jazzcash.refund import RefundClient

logger = logging.getLogger(__name__)


class MWalletPaymentView(APIView):
    """
    Initiate MWallet payment

    POST /api/payments/jazzcash/mwallet/initiate/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MWalletPaymentRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Get event
        event = get_object_or_404(Event, id=data['event_id'])

        # Check if event requires payment
        if not getattr(event, 'is_paid_event', False):
            return Response(
                {'error': 'This event does not require payment'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Don't create registration yet - only create after successful payment
        # Check if already registered
        existing_registration = Registration.objects.filter(
            event=event,
            user=request.user
        ).first()

        # Initiate payment
        client = MWalletClient()
        success, response_data, message = client.initiate_payment(
            event=event,
            user=request.user,
            amount=data['amount'],
            mobile_number=data['mobile_number'],
            cnic=data['cnic'],
            description=data.get('description', ''),
            registration=existing_registration  # Pass existing or None
        )

        if success:
            return Response({
                'success': True,
                'message': message,
                'data': response_data,
                'txn_ref_no': response_data.get('pp_TxnRefNo'),
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': message,
                'data': response_data,
            }, status=status.HTTP_400_BAD_REQUEST)


class CardPaymentView(APIView):
    """
    Initiate Card payment (returns form data for redirection)

    POST /api/payments/jazzcash/card/initiate/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CardPaymentRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Get event
        event = get_object_or_404(Event, id=data['event_id'])

        # Check if event requires payment
        if not getattr(event, 'is_paid_event', False):
            return Response(
                {'error': 'This event does not require payment'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Don't create registration yet - only create after successful payment
        # Check if already registered
        existing_registration = Registration.objects.filter(
            event=event,
            user=request.user
        ).first()

        # Prepare payment form
        handler = CardPaymentHandler()
        success, form_data, message = handler.prepare_payment_form(
            event=event,
            user=request.user,
            amount=data['amount'],
            description=data.get('description', ''),
            registration=existing_registration  # Pass existing or None
        )

        if success:
            return Response({
                'success': True,
                'form_data': form_data,
                'message': 'Payment form prepared',
                'txn_ref_no': form_data.get('txn_ref_no'),  # Include txn_ref_no at top level
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)


class SessionMWalletPaymentView(APIView):
    """
    Initiate MWallet payment for session

    POST /api/payments/jazzcash/session/mwallet/initiate/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("\n" + "="*80)
        print("🔷 SESSION MWALLET PAYMENT REQUEST RECEIVED")
        print("="*80)
        print(f"User: {request.user.username} (ID: {request.user.id})")
        print(f"Request Data: {request.data}")
        print("="*80 + "\n")

        try:
            serializer = MWalletPaymentRequestSerializer(data=request.data)

            if not serializer.is_valid():
                print(f"❌ Serializer validation failed: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data
            print(f"✅ Serializer validated successfully")
            print(f"Validated data: {data}")

            # Get session instead of event
            session_id = data.get('session_id')
            print(f"\n📋 Step 1: Getting session with ID: {session_id}")

            session = get_object_or_404(Session, id=session_id)
            print(f"✅ Session found:")
            print(f"   - ID: {session.id}")
            print(f"   - Title: {session.title}")
            print(f"   - Has direct event field: {hasattr(session, 'event')}")
            print(f"   - Direct event value: {session.event if hasattr(session, 'event') else 'N/A'}")
            print(f"   - Has agenda field: {hasattr(session, 'agenda')}")
            print(f"   - Agenda value: {session.agenda if hasattr(session, 'agenda') else 'N/A'}")
            print(f"   - Agenda ID: {session.agenda.id if session.agenda else 'N/A'}")
            print(f"   - is_paid_session: {getattr(session, 'is_paid_session', False)}")
            print(f"   - session_fee: {getattr(session, 'session_fee', 'N/A')}")

            # Check if session requires payment
            if not getattr(session, 'is_paid_session', False):
                print(f"❌ Session does not require payment")
                return Response(
                    {'error': 'This session does not require payment'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            print(f"✅ Session requires payment")

            # Don't create session registration yet - only create after successful payment
            # Check if already registered
            print(f"\n📋 Step 2: Checking existing session registration...")
            existing_session_registration = SessionRegistration.objects.filter(
                session=session,
                user=request.user
            ).first()
            if existing_session_registration:
                print(f"✅ Found existing session registration: ID {existing_session_registration.id}")
            else:
                print(f"✅ No existing session registration found")

            # Get event through agenda relationship
            print(f"\n📋 Step 3: Getting event through agenda relationship...")
            print(f"Session object details before calling get_event():")
            print(f"   - session: {session}")
            print(f"   - session type: {type(session)}")
            print(f"   - session.__dict__: {session.__dict__ if hasattr(session, '__dict__') else 'N/A'}")

            print(f"\nCalling session.get_event()...")
            try:
                event = session.get_event()
                print(f"✅ get_event() completed successfully")
            except Exception as e:
                print(f"❌ ERROR in session.get_event(): {type(e).__name__}: {str(e)}")
                import traceback
                print(traceback.format_exc())
                return Response(
                    {'error': f'Error getting event from session: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            print(f"\nResult: {event}")
            if event:
                print(f"✅ Event found:")
                print(f"   - ID: {event.id}")
                print(f"   - Title: {event.title}")
            else:
                print(f"❌ Event is None!")
                print(f"   - Session.event: {session.event if hasattr(session, 'event') else 'N/A'}")
                print(f"   - Session.agenda: {session.agenda}")
                if session.agenda:
                    print(f"   - Session.agenda.event: {session.agenda.event if hasattr(session.agenda, 'event') else 'N/A'}")

            if not event:
                print(f"❌ FAILED: Session is not associated with any event")
                return Response(
                    {'error': 'Session is not associated with any event. Please ensure the session is linked to an event through an agenda.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Initiate payment
            print(f"\n📋 Step 4: Initiating MWallet payment...")
            print(f"Payment details:")
            print(f"   - Event: {event.title} (ID: {event.id})")
            print(f"   - Session: {session.title} (ID: {session.id})")
            print(f"   - Amount: {data['amount']}")
            print(f"   - Mobile: {data['mobile_number']}")
            print(f"   - CNIC: {data['cnic']}")

            client = MWalletClient()
            print(f"\n📋 Calling client.initiate_payment() with:")
            print(f"   - event: {event} (type: {type(event).__name__})")
            print(f"   - user: {request.user} (type: {type(request.user).__name__})")
            print(f"   - session: {session} (type: {type(session).__name__})")

            success, response_data, message = client.initiate_payment(
                event=event,
                user=request.user,
                amount=data['amount'],
                mobile_number=data['mobile_number'],
                cnic=data['cnic'],
                description=data.get('description', f'Payment for session: {session.title}'),
                session=session,
                session_registration=existing_session_registration  # Pass existing or None
            )

            if success:
                print(f"✅ Payment initiated successfully")
                print(f"   - TxnRefNo: {response_data.get('pp_TxnRefNo')}")
                return Response({
                    'success': True,
                    'message': message,
                    'data': response_data,
                    'txn_ref_no': response_data.get('pp_TxnRefNo'),
                }, status=status.HTTP_200_OK)
            else:
                print(f"❌ Payment initiation failed: {message}")
                return Response({
                    'success': False,
                    'error': message,
                    'data': response_data,
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"\n❌ EXCEPTION OCCURRED!")
            print(f"Exception type: {type(e).__name__}")
            print(f"Exception message: {str(e)}")
            import traceback
            print(f"Traceback:")
            print(traceback.format_exc())
            logger.error(f"Session MWallet payment error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': f'Error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class SessionCardPaymentView(APIView):
    """
    Initiate Card payment for session (returns form data for redirection)

    POST /api/payments/jazzcash/session/card/initiate/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("\n" + "="*80)
        print("🔷 SESSION CARD PAYMENT REQUEST RECEIVED")
        print("="*80)
        print(f"User: {request.user.username} (ID: {request.user.id})")
        print(f"Request Data: {request.data}")
        print("="*80 + "\n")

        try:
            serializer = CardPaymentRequestSerializer(data=request.data)

            if not serializer.is_valid():
                print(f"❌ Serializer validation failed: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data
            print(f"✅ Serializer validated successfully")
            print(f"Validated data: {data}")

            # Get session
            session_id = data.get('session_id')
            print(f"\n📋 Step 1: Getting session with ID: {session_id}")

            session = get_object_or_404(Session, id=session_id)
            print(f"✅ Session found:")
            print(f"   - ID: {session.id}")
            print(f"   - Title: {session.title}")
            print(f"   - Has direct event field: {hasattr(session, 'event')}")
            print(f"   - Direct event value: {session.event if hasattr(session, 'event') else 'N/A'}")
            print(f"   - Has agenda field: {hasattr(session, 'agenda')}")
            print(f"   - Agenda value: {session.agenda if hasattr(session, 'agenda') else 'N/A'}")
            print(f"   - Agenda ID: {session.agenda.id if session.agenda else 'N/A'}")
            print(f"   - is_paid_session: {getattr(session, 'is_paid_session', False)}")
            print(f"   - session_fee: {getattr(session, 'session_fee', 'N/A')}")

            # Check if session requires payment
            if not getattr(session, 'is_paid_session', False):
                print(f"❌ Session does not require payment")
                return Response(
                    {'error': 'This session does not require payment'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            print(f"✅ Session requires payment")

            # Don't create session registration yet - only create after successful payment
            # Check if already registered
            print(f"\n📋 Step 2: Checking existing session registration...")
            existing_session_registration = SessionRegistration.objects.filter(
                session=session,
                user=request.user
            ).first()
            if existing_session_registration:
                print(f"✅ Found existing session registration: ID {existing_session_registration.id}")
            else:
                print(f"✅ No existing session registration found")

            # Get event through agenda relationship
            print(f"\n📋 Step 3: Getting event through agenda relationship...")
            print(f"Session object details before calling get_event():")
            print(f"   - session: {session}")
            print(f"   - session type: {type(session)}")
            print(f"   - session.__dict__: {session.__dict__ if hasattr(session, '__dict__') else 'N/A'}")

            print(f"\nCalling session.get_event()...")
            try:
                event = session.get_event()
                print(f"✅ get_event() completed successfully")
            except Exception as e:
                print(f"❌ ERROR in session.get_event(): {type(e).__name__}: {str(e)}")
                import traceback
                print(traceback.format_exc())
                return Response(
                    {'error': f'Error getting event from session: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            print(f"\nResult: {event}")
            if event:
                print(f"✅ Event found:")
                print(f"   - ID: {event.id}")
                print(f"   - Title: {event.title}")
            else:
                print(f"❌ Event is None!")
                print(f"   - Session.event: {session.event if hasattr(session, 'event') else 'N/A'}")
                print(f"   - Session.agenda: {session.agenda}")
                if session.agenda:
                    print(f"   - Session.agenda.event: {session.agenda.event if hasattr(session.agenda, 'event') else 'N/A'}")

            if not event:
                print(f"❌ FAILED: Session is not associated with any event")
                return Response(
                    {'error': 'Session is not associated with any event. Please ensure the session is linked to an event through an agenda.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Prepare payment form
            print(f"\n📋 Step 4: Preparing card payment form...")
            print(f"Payment details:")
            print(f"   - Event: {event.title} (ID: {event.id})")
            print(f"   - Session: {session.title} (ID: {session.id})")
            print(f"   - Amount: {data['amount']}")

            handler = CardPaymentHandler()
            print(f"\n📋 Calling handler.prepare_payment_form() with:")
            print(f"   - event: {event} (type: {type(event).__name__})")
            print(f"   - user: {request.user} (type: {type(request.user).__name__})")
            print(f"   - session: {session} (type: {type(session).__name__})")

            success, form_data, message = handler.prepare_payment_form(
                event=event,
                user=request.user,
                amount=data['amount'],
                description=data.get('description', f'Payment for session: {session.title}'),
                session=session,
                session_registration=existing_session_registration  # Pass existing or None
            )

            if success:
                print(f"✅ Payment form prepared successfully")
                print(f"   - TxnRefNo: {form_data.get('txn_ref_no')}")
                return Response({
                    'success': True,
                    'form_data': form_data,
                    'message': 'Payment form prepared',
                    'txn_ref_no': form_data.get('txn_ref_no'),  # Include txn_ref_no at top level
                }, status=status.HTTP_200_OK)
            else:
                print(f"❌ Payment form preparation failed: {message}")
                return Response({
                    'success': False,
                    'error': message
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"\n❌ EXCEPTION OCCURRED!")
            print(f"Exception type: {type(e).__name__}")
            print(f"Exception message: {str(e)}")
            import traceback
            print(f"Traceback:")
            print(traceback.format_exc())
            logger.error(f"Session Card payment error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': f'Error: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def payment_return_view(request):
    """
    Handle return from JazzCash payment gateway

    GET/POST /api/payments/jazzcash/return/
    """
    try:
        print(f"\n{'='*80}")
        print(f"🌐 PAYMENT RETURN VIEW CALLED")
        print(f"{'='*80}")
        print(f"Method: {request.method}")

        # Get response data (could be GET or POST)
        response_data = request.POST.dict() if request.method == 'POST' else request.GET.dict()

        print(f"Response data:")
        for key, value in response_data.items():
            print(f"   {key}: {value}")
        print(f"{'='*80}\n")

        logger.info(f"Payment return received: {response_data}")

        print(f"📋 Calling CardPaymentHandler.handle_return_response()...")
        handler = CardPaymentHandler()
        success, transaction, message = handler.handle_return_response(response_data)

        print(f"\n📤 Handler returned:")
        print(f"   success: {success}")
        print(f"   transaction: {transaction.id if transaction else None}")
        print(f"   message: {message}")

        # Render response page
        context = {
            'success': success,
            'message': message,
            'transaction': transaction,
        }

        print(f"\n📄 Rendering template with context:")
        print(f"   success: {context['success']}")
        print(f"   message: {context['message']}")
        print(f"   transaction: {context['transaction']}")
        print(f"{'='*80}\n")

        return render(request, 'payments/payment_return.html', context)

    except Exception as e:
        print(f"\n❌ EXCEPTION in payment_return_view!")
        print(f"   Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        logger.error(f"Error in payment return: {str(e)}", exc_info=True)
        return render(request, 'payments/payment_return.html', {
            'success': False,
            'message': f'Error: {str(e)}',
            'transaction': None,
        })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def ipn_listener_view(request):
    """
    IPN Listener endpoint for JazzCash

    POST /api/payments/jazzcash/ipn/
    """
    print("ipn received")
    try:
        ipn_data = request.data if hasattr(request, 'data') else request.POST.dict()

        logger.info(f"IPN received: {ipn_data}")
        print(f"IPN received: {ipn_data}")

        handler = IPNHandler()
        success, response_data, message = handler.process_ipn(ipn_data)

        logger.info(f"IPN response: {response_data}")
        print(f"IPN response: {response_data}")

        return JsonResponse(response_data, status=200 if success else 400)

    except Exception as e:
        logger.error(f"IPN error: {str(e)}", exc_info=True)
        return JsonResponse({
            'pp_ResponseCode': '999',
            'pp_ResponseMessage': 'IPN processing failed',
            'pp_SecureHash': ''
        }, status=500)


class StatusInquiryView(APIView):
    """
    Check transaction status

    POST /api/payments/jazzcash/status-inquiry/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StatusInquiryRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        client = StatusInquiryClient()
        success, response_data, message = client.inquire_transaction(
            txn_ref_no=data['txn_ref_no'],
            inquired_by=request.user
        )

        if success:
            return Response({
                'success': True,
                'data': response_data,
                'message': message
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': message,
                'data': response_data
            }, status=status.HTTP_400_BAD_REQUEST)


class RefundView(APIView):
    """
    Process refund

    POST /api/payments/jazzcash/refund/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RefundRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        client = RefundClient()
        success, refund, message = client.process_refund(
            txn_ref_no=data['txn_ref_no'],
            refund_amount=data['refund_amount'],
            reason=data['reason'],
            initiated_by=request.user
        )

        if success:
            serializer = JazzCashRefundSerializer(refund)
            return Response({
                'success': True,
                'refund': serializer.data,
                'message': message
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)


class TransactionListView(generics.ListAPIView):
    """
    List user's transactions

    GET /api/payments/transactions/
    """
    serializer_class = JazzCashTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return JazzCashTransaction.objects.filter(user=self.request.user)


class TransactionDetailView(generics.RetrieveAPIView):
    """
    Get transaction details

    GET /api/payments/transactions/{txn_ref_no}/
    """
    serializer_class = JazzCashTransactionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'txn_ref_no'

    def get_queryset(self):
        return JazzCashTransaction.objects.filter(user=self.request.user)


class CheckTransactionStatusView(APIView):
    """
    Check transaction status from local database (simple check without calling JazzCash)

    POST /api/payments/transactions/check-status/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        txn_ref_no = request.data.get('txn_ref_no')

        if not txn_ref_no:
            return Response({
                'success': False,
                'error': 'Transaction reference number is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            transaction = JazzCashTransaction.objects.get(
                txn_ref_no=txn_ref_no,
                user=request.user
            )

            serializer = JazzCashTransactionSerializer(transaction)

            return Response({
                'success': True,
                'transaction': serializer.data,
                'status': transaction.status,
                'payment_status': transaction.status,  # Use our status
                'message': f'Transaction {transaction.get_status_display()}'
            }, status=status.HTTP_200_OK)

        except JazzCashTransaction.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Transaction not found',
                'status': 'not_found'
            }, status=status.HTTP_404_NOT_FOUND)


class RefundHistoryView(generics.ListAPIView):
    """
    Get refund history for a transaction

    GET /api/payments/transactions/{txn_ref_no}/refunds/
    """
    serializer_class = JazzCashRefundSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        txn_ref_no = self.kwargs.get('txn_ref_no')
        transaction = get_object_or_404(
            JazzCashTransaction,
            txn_ref_no=txn_ref_no,
            user=self.request.user
        )
        return transaction.refunds.all()
