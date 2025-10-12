"""
URL Configuration for JazzCash Payments
"""

from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Event Payment Initiation
    path('jazzcash/mwallet/initiate/', views.MWalletPaymentView.as_view(), name='mwallet_initiate'),
    path('jazzcash/card/initiate/', views.CardPaymentView.as_view(), name='card_initiate'),

    # Session Payment Initiation
    path('jazzcash/session/mwallet/initiate/', views.SessionMWalletPaymentView.as_view(), name='session_mwallet_initiate'),
    path('jazzcash/session/card/initiate/', views.SessionCardPaymentView.as_view(), name='session_card_initiate'),

    # Callbacks
    path('jazzcash/return/', views.payment_return_view, name='payment_return'),
    path('jazzcash/ipn/', views.ipn_listener_view, name='ipn_listener'),

    # Transaction Management
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('transactions/check-status/', views.CheckTransactionStatusView.as_view(), name='check_transaction_status'),
    path('transactions/<str:txn_ref_no>/', views.TransactionDetailView.as_view(), name='transaction_detail'),
    path('transactions/<str:txn_ref_no>/refunds/', views.RefundHistoryView.as_view(), name='refund_history'),

    # Operations
    path('jazzcash/status-inquiry/', views.StatusInquiryView.as_view(), name='status_inquiry'),
    path('jazzcash/refund/', views.RefundView.as_view(), name='refund'),
]
