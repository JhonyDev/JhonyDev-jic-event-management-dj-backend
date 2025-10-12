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
        serializer = MWalletPaymentRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Get session instead of event
        session = get_object_or_404(Session, id=data.get('session_id'))

        # Check if session requires payment
        if not getattr(session, 'is_paid_session', False):
            return Response(
                {'error': 'This session does not require payment'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Don't create session registration yet - only create after successful payment
        # Check if already registered
        existing_session_registration = SessionRegistration.objects.filter(
            session=session,
            user=request.user
        ).first()

        # Initiate payment
        client = MWalletClient()
        success, response_data, message = client.initiate_payment(
            event=session.event,  # Still need event for context
            user=request.user,
            amount=data['amount'],
            mobile_number=data['mobile_number'],
            cnic=data['cnic'],
            description=data.get('description', f'Payment for session: {session.title}'),
            session=session,
            session_registration=existing_session_registration  # Pass existing or None
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


class SessionCardPaymentView(APIView):
    """
    Initiate Card payment for session (returns form data for redirection)

    POST /api/payments/jazzcash/session/card/initiate/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CardPaymentRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Get session
        session = get_object_or_404(Session, id=data.get('session_id'))

        # Check if session requires payment
        if not getattr(session, 'is_paid_session', False):
            return Response(
                {'error': 'This session does not require payment'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Don't create session registration yet - only create after successful payment
        # Check if already registered
        existing_session_registration = SessionRegistration.objects.filter(
            session=session,
            user=request.user
        ).first()

        # Prepare payment form
        handler = CardPaymentHandler()
        success, form_data, message = handler.prepare_payment_form(
            event=session.event,
            user=request.user,
            amount=data['amount'],
            description=data.get('description', f'Payment for session: {session.title}'),
            session=session,
            session_registration=existing_session_registration  # Pass existing or None
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


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def payment_return_view(request):
    """
    Handle return from JazzCash payment gateway

    GET/POST /api/payments/jazzcash/return/
    """
    try:
        # Get response data (could be GET or POST)
        response_data = request.POST.dict() if request.method == 'POST' else request.GET.dict()

        logger.info(f"Payment return received: {response_data}")

        handler = CardPaymentHandler()
        success, transaction, message = handler.handle_return_response(response_data)

        # Render response page
        context = {
            'success': success,
            'message': message,
            'transaction': transaction,
        }

        return render(request, 'payments/payment_return.html', context)

    except Exception as e:
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
