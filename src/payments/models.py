from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class JazzCashTransaction(models.Model):
    """
    Main transaction model for tracking JazzCash payments
    """
    TRANSACTION_TYPES = [
        ('MWALLET', 'Mobile Wallet'),
        ('MPAY', 'Card Payment'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    # Core fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey('api.Event', on_delete=models.CASCADE, related_name='jazzcash_transactions', null=True, blank=True)
    session = models.ForeignKey('api.Session', on_delete=models.CASCADE, related_name='jazzcash_transactions', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='jazzcash_transactions')
    registration = models.ForeignKey('api.Registration', on_delete=models.CASCADE, related_name='jazzcash_transactions', null=True, blank=True)
    session_registration = models.ForeignKey('api.SessionRegistration', on_delete=models.CASCADE, related_name='jazzcash_transactions', null=True, blank=True)

    # Transaction details
    txn_ref_no = models.CharField(max_length=20, unique=True, db_index=True)
    txn_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Actual amount in PKR
    amount_in_paisa = models.BigIntegerField()  # Amount * 100 (as sent to JazzCash)
    currency = models.CharField(max_length=3, default='PKR')

    # Transaction metadata
    bill_reference = models.CharField(max_length=20)
    description = models.CharField(max_length=200)

    # Mobile wallet specific
    mobile_number = models.CharField(max_length=11, blank=True)  # 03XXXXXXXXX
    cnic = models.CharField(max_length=6, blank=True)  # Last 6 digits

    # JazzCash response fields
    pp_response_code = models.CharField(max_length=10, blank=True)
    pp_response_message = models.TextField(blank=True)
    pp_retrieval_ref_no = models.CharField(max_length=50, blank=True)
    pp_auth_code = models.CharField(max_length=50, blank=True)
    pp_txn_type = models.CharField(max_length=20, blank=True)
    pp_version = models.CharField(max_length=10, blank=True)

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Additional data (store complete request/response)
    request_data = models.JSONField(default=dict, blank=True)
    response_data = models.JSONField(default=dict, blank=True)

    # Refund tracking
    total_refunded_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_refundable = models.BooleanField(default=True)

    # Security tracking
    hash_verification_warning = models.BooleanField(default=False, help_text="True if payment succeeded but hash verification failed")

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'JazzCash Transaction'
        verbose_name_plural = 'JazzCash Transactions'
        indexes = [
            models.Index(fields=['txn_ref_no']),
            models.Index(fields=['status']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['event', '-created_at']),
        ]

    def __str__(self):
        return f"{self.txn_ref_no} - {self.user.email} - {self.get_status_display()}"

    def mark_completed(self, response_data):
        """Mark transaction as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.response_data = response_data
        self.pp_response_code = response_data.get('pp_ResponseCode', '')
        self.pp_response_message = response_data.get('pp_ResponseMessage', '')
        self.pp_retrieval_ref_no = response_data.get('pp_RetreivalReferenceNo', '')
        self.pp_auth_code = response_data.get('pp_AuthCode', '')
        self.save()

    def mark_failed(self, response_data):
        """Mark transaction as failed"""
        self.status = 'failed'
        self.response_data = response_data
        self.pp_response_code = response_data.get('pp_ResponseCode', '')
        self.pp_response_message = response_data.get('pp_ResponseMessage', '')
        self.save()

    def can_refund(self, amount=None):
        """Check if transaction can be refunded"""
        if not self.is_refundable:
            return False, "Transaction is not refundable"
        if self.status != 'completed':
            return False, "Only completed transactions can be refunded"

        if amount:
            available_amount = self.amount - self.total_refunded_amount
            if amount > available_amount:
                return False, f"Refund amount exceeds available amount ({available_amount})"

        return True, "Refund allowed"

    @property
    def is_completed(self):
        return self.status == 'completed'

    @property
    def is_pending(self):
        return self.status == 'pending'


class JazzCashRefund(models.Model):
    """
    Track refund transactions
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_transaction = models.ForeignKey(JazzCashTransaction, on_delete=models.CASCADE, related_name='refunds')

    # Refund details
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    refund_reason = models.TextField()
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='initiated_refunds')

    # JazzCash response
    response_code = models.CharField(max_length=10, blank=True)
    response_message = models.TextField(blank=True)
    secure_hash = models.CharField(max_length=64, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Store full response
    request_data = models.JSONField(default=dict, blank=True)
    response_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'JazzCash Refund'
        verbose_name_plural = 'JazzCash Refunds'

    def __str__(self):
        return f"Refund {self.refund_amount} for {self.original_transaction.txn_ref_no}"

    def mark_completed(self, response_data):
        """Mark refund as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.response_data = response_data
        self.response_code = response_data.get('responseCode', '')
        self.response_message = response_data.get('responseMessage', '')
        self.secure_hash = response_data.get('secureHash', '')
        self.save()

        # Update original transaction
        self.original_transaction.total_refunded_amount += self.refund_amount
        if self.original_transaction.total_refunded_amount >= self.original_transaction.amount:
            self.original_transaction.status = 'refunded'
        else:
            self.original_transaction.status = 'partially_refunded'
        self.original_transaction.save()


class JazzCashIPNLog(models.Model):
    """
    Log all IPN (Instant Payment Notification) received from JazzCash
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(JazzCashTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='ipn_logs')

    # IPN data
    txn_ref_no = models.CharField(max_length=20, db_index=True)
    txn_type = models.CharField(max_length=20)
    response_code = models.CharField(max_length=10)
    response_message = models.TextField()

    # Complete IPN payload
    ipn_data = models.JSONField(default=dict)

    # Verification
    secure_hash_received = models.CharField(max_length=64)
    secure_hash_calculated = models.CharField(max_length=64, blank=True)
    is_verified = models.BooleanField(default=False)

    # Response sent back to JazzCash
    response_sent = models.JSONField(default=dict, blank=True)

    # Timestamp
    received_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    # Retry tracking (JazzCash retries 3 times)
    retry_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-received_at']
        verbose_name = 'JazzCash IPN Log'
        verbose_name_plural = 'JazzCash IPN Logs'
        indexes = [
            models.Index(fields=['txn_ref_no']),
            models.Index(fields=['-received_at']),
        ]

    def __str__(self):
        return f"IPN for {self.txn_ref_no} - {self.response_code}"


class JazzCashStatusInquiry(models.Model):
    """
    Track status inquiry requests
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(JazzCashTransaction, on_delete=models.CASCADE, related_name='status_inquiries')

    # Inquiry details
    inquired_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    inquired_at = models.DateTimeField(auto_now_add=True)

    # Request data
    request_data = models.JSONField(default=dict)

    # Response from JazzCash
    response_code = models.CharField(max_length=10, blank=True)
    response_message = models.TextField(blank=True)
    payment_response_code = models.CharField(max_length=10, blank=True)  # Actual transaction status
    payment_response_message = models.TextField(blank=True)
    payment_status = models.CharField(max_length=20, blank=True)  # Completed, Pending, etc.

    # Full response
    response_data = models.JSONField(default=dict, blank=True)

    # Success/Failure
    success = models.BooleanField(default=False)

    class Meta:
        ordering = ['-inquired_at']
        verbose_name = 'JazzCash Status Inquiry'
        verbose_name_plural = 'JazzCash Status Inquiries'

    def __str__(self):
        return f"Inquiry for {self.transaction.txn_ref_no} at {self.inquired_at}"
