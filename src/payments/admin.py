"""
Django Admin Configuration for JazzCash Payments
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    JazzCashTransaction,
    JazzCashRefund,
    JazzCashIPNLog,
    JazzCashStatusInquiry
)


@admin.register(JazzCashTransaction)
class JazzCashTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'txn_ref_no', 'user', 'event', 'amount', 'status_badge',
        'txn_type', 'created_at'
    ]
    list_filter = ['status', 'txn_type', 'created_at', 'event']
    search_fields = [
        'txn_ref_no', 'user__email', 'mobile_number',
        'pp_retrieval_ref_no', 'bill_reference'
    ]
    readonly_fields = [
        'id', 'txn_ref_no', 'amount_in_paisa', 'pp_response_code',
        'pp_response_message', 'pp_retrieval_ref_no', 'pp_auth_code',
        'created_at', 'updated_at', 'completed_at',
        'request_data_display', 'response_data_display'
    ]
    fieldsets = (
        ('Transaction Details', {
            'fields': (
                'id', 'event', 'user', 'registration',
                'txn_ref_no', 'txn_type', 'status'
            )
        }),
        ('Payment Information', {
            'fields': (
                'amount', 'amount_in_paisa', 'currency',
                'bill_reference', 'description'
            )
        }),
        ('MWallet Specific', {
            'fields': ('mobile_number', 'cnic'),
            'classes': ('collapse',)
        }),
        ('JazzCash Response', {
            'fields': (
                'pp_response_code', 'pp_response_message',
                'pp_retrieval_ref_no', 'pp_auth_code',
                'pp_txn_type', 'pp_version'
            )
        }),
        ('Refund Information', {
            'fields': ('total_refunded_amount', 'is_refundable')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
        ('Raw Data', {
            'fields': ('request_data_display', 'response_data_display'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        colors = {
            'completed': 'green',
            'pending': 'orange',
            'failed': 'red',
            'refunded': 'purple',
            'partially_refunded': 'blue',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def request_data_display(self, obj):
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.request_data, indent=2))
    request_data_display.short_description = 'Request Data'

    def response_data_display(self, obj):
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.response_data, indent=2))
    response_data_display.short_description = 'Response Data'


@admin.register(JazzCashRefund)
class JazzCashRefundAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'original_transaction', 'refund_amount',
        'status_badge', 'initiated_by', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = [
        'original_transaction__txn_ref_no',
        'initiated_by__email', 'refund_reason'
    ]
    readonly_fields = [
        'id', 'original_transaction', 'response_code',
        'response_message', 'secure_hash', 'created_at',
        'completed_at', 'request_data_display', 'response_data_display'
    ]
    fieldsets = (
        ('Refund Details', {
            'fields': (
                'id', 'original_transaction', 'refund_amount',
                'refund_reason', 'initiated_by', 'status'
            )
        }),
        ('Response', {
            'fields': ('response_code', 'response_message', 'secure_hash')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at')
        }),
        ('Raw Data', {
            'fields': ('request_data_display', 'response_data_display'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        colors = {
            'completed': 'green',
            'pending': 'orange',
            'failed': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def request_data_display(self, obj):
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.request_data, indent=2))
    request_data_display.short_description = 'Request Data'

    def response_data_display(self, obj):
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.response_data, indent=2))
    response_data_display.short_description = 'Response Data'


@admin.register(JazzCashIPNLog)
class JazzCashIPNLogAdmin(admin.ModelAdmin):
    list_display = [
        'txn_ref_no', 'response_code', 'verified_badge',
        'processed_badge', 'retry_count', 'received_at'
    ]
    list_filter = ['is_verified', 'processed', 'received_at']
    search_fields = ['txn_ref_no', 'response_code']
    readonly_fields = [
        'id', 'transaction', 'txn_ref_no', 'txn_type',
        'response_code', 'response_message', 'secure_hash_received',
        'secure_hash_calculated', 'is_verified', 'received_at',
        'processed', 'processed_at', 'retry_count',
        'ipn_data_display', 'response_sent_display'
    ]
    fieldsets = (
        ('IPN Details', {
            'fields': (
                'id', 'transaction', 'txn_ref_no', 'txn_type',
                'response_code', 'response_message'
            )
        }),
        ('Verification', {
            'fields': (
                'secure_hash_received', 'secure_hash_calculated',
                'is_verified'
            )
        }),
        ('Processing', {
            'fields': ('processed', 'processed_at', 'retry_count')
        }),
        ('Timestamps', {
            'fields': ('received_at',)
        }),
        ('Raw Data', {
            'fields': ('ipn_data_display', 'response_sent_display'),
            'classes': ('collapse',)
        }),
    )

    def verified_badge(self, obj):
        color = 'green' if obj.is_verified else 'red'
        text = 'Verified' if obj.is_verified else 'Not Verified'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, text
        )
    verified_badge.short_description = 'Verification'

    def processed_badge(self, obj):
        color = 'green' if obj.processed else 'orange'
        text = 'Processed' if obj.processed else 'Pending'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, text
        )
    processed_badge.short_description = 'Status'

    def ipn_data_display(self, obj):
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.ipn_data, indent=2))
    ipn_data_display.short_description = 'IPN Data'

    def response_sent_display(self, obj):
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.response_sent, indent=2))
    response_sent_display.short_description = 'Response Sent'


@admin.register(JazzCashStatusInquiry)
class JazzCashStatusInquiryAdmin(admin.ModelAdmin):
    list_display = [
        'transaction', 'payment_response_code',
        'payment_status', 'success_badge', 'inquired_at'
    ]
    list_filter = ['success', 'payment_status', 'inquired_at']
    search_fields = ['transaction__txn_ref_no']
    readonly_fields = [
        'id', 'transaction', 'inquired_by', 'inquired_at',
        'response_code', 'response_message',
        'payment_response_code', 'payment_response_message',
        'payment_status', 'success',
        'request_data_display', 'response_data_display'
    ]
    fieldsets = (
        ('Inquiry Details', {
            'fields': (
                'id', 'transaction', 'inquired_by', 'inquired_at', 'success'
            )
        }),
        ('API Response', {
            'fields': ('response_code', 'response_message')
        }),
        ('Payment Status', {
            'fields': (
                'payment_response_code', 'payment_response_message',
                'payment_status'
            )
        }),
        ('Raw Data', {
            'fields': ('request_data_display', 'response_data_display'),
            'classes': ('collapse',)
        }),
    )

    def success_badge(self, obj):
        color = 'green' if obj.success else 'red'
        text = 'Success' if obj.success else 'Failed'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, text
        )
    success_badge.short_description = 'Result'

    def request_data_display(self, obj):
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.request_data, indent=2))
    request_data_display.short_description = 'Request Data'

    def response_data_display(self, obj):
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.response_data, indent=2))
    response_data_display.short_description = 'Response Data'
