"""
DRF Serializers for JazzCash Payments
"""

from rest_framework import serializers
from .models import JazzCashTransaction, JazzCashRefund, JazzCashIPNLog, JazzCashStatusInquiry


class JazzCashTransactionSerializer(serializers.ModelSerializer):
    """Serializer for JazzCash transactions"""

    event_title = serializers.CharField(source='event.title', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    txn_type_display = serializers.CharField(source='get_txn_type_display', read_only=True)
    is_refundable = serializers.BooleanField(read_only=True)

    class Meta:
        model = JazzCashTransaction
        fields = [
            'id', 'event', 'event_title', 'user', 'user_email',
            'txn_ref_no', 'txn_type', 'txn_type_display',
            'amount', 'currency', 'bill_reference', 'description',
            'mobile_number', 'cnic',
            'pp_response_code', 'pp_response_message',
            'pp_retrieval_ref_no', 'pp_auth_code',
            'status', 'status_display', 'is_refundable',
            'created_at', 'updated_at', 'completed_at',
            'total_refunded_amount',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class JazzCashRefundSerializer(serializers.ModelSerializer):
    """Serializer for JazzCash refunds"""

    transaction_ref = serializers.CharField(source='original_transaction.txn_ref_no', read_only=True)
    initiated_by_name = serializers.CharField(source='initiated_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = JazzCashRefund
        fields = [
            'id', 'original_transaction', 'transaction_ref',
            'refund_amount', 'refund_reason',
            'initiated_by', 'initiated_by_name',
            'response_code', 'response_message',
            'status', 'status_display',
            'created_at', 'completed_at',
        ]
        read_only_fields = ['id', 'created_at', 'completed_at']


class MWalletPaymentRequestSerializer(serializers.Serializer):
    """Serializer for MWallet payment request"""

    event_id = serializers.IntegerField(required=False)
    session_id = serializers.IntegerField(required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    mobile_number = serializers.CharField(max_length=11)
    cnic = serializers.CharField(max_length=6)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate(self, data):
        """Ensure either event_id or session_id is provided"""
        if not data.get('event_id') and not data.get('session_id'):
            raise serializers.ValidationError("Either event_id or session_id must be provided")
        return data


class CardPaymentRequestSerializer(serializers.Serializer):
    """Serializer for Card payment request"""

    event_id = serializers.IntegerField(required=False)
    session_id = serializers.IntegerField(required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate(self, data):
        """Ensure either event_id or session_id is provided"""
        if not data.get('event_id') and not data.get('session_id'):
            raise serializers.ValidationError("Either event_id or session_id must be provided")
        return data


class RefundRequestSerializer(serializers.Serializer):
    """Serializer for refund request"""

    txn_ref_no = serializers.CharField(max_length=20)
    refund_amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    reason = serializers.CharField(max_length=500)


class StatusInquiryRequestSerializer(serializers.Serializer):
    """Serializer for status inquiry request"""

    txn_ref_no = serializers.CharField(max_length=20)
