"""
JazzCash Configuration Manager
==============================

Centralized configuration management for JazzCash integration
"""

from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class JazzCashConfig:
    """
    JazzCash configuration manager
    """

    def __init__(self):
        self.config = getattr(settings, 'JAZZCASH_CONFIG', {})
        self._validate_config()

    def _validate_config(self):
        """Validate that all required configuration is present"""
        required_fields = ['MERCHANT_ID', 'PASSWORD', 'INTEGRITY_SALT']

        missing_fields = [field for field in required_fields if not self.config.get(field)]

        if missing_fields:
            logger.warning(f"Missing JazzCash configuration: {', '.join(missing_fields)}")

    @property
    def merchant_id(self):
        """Get Merchant ID"""
        return self.config.get('MERCHANT_ID', '')

    @property
    def password(self):
        """Get Password"""
        return self.config.get('PASSWORD', '')

    @property
    def integrity_salt(self):
        """Get Integrity Salt / Hash Key"""
        return self.config.get('INTEGRITY_SALT', '')

    @property
    def return_url(self):
        """Get Return URL"""
        return self.config.get('RETURN_URL', '')

    @property
    def ipn_url(self):
        """Get IPN URL"""
        return self.config.get('IPN_URL', '')

    @property
    def environment(self):
        """Get environment (sandbox/production)"""
        return self.config.get('ENVIRONMENT', 'sandbox')

    @property
    def currency(self):
        """Get currency"""
        return self.config.get('CURRENCY', 'PKR')

    @property
    def language(self):
        """Get language"""
        return self.config.get('LANGUAGE', 'EN')

    @property
    def is_sandbox(self):
        """Check if running in sandbox mode"""
        return self.environment.lower() == 'sandbox'

    @property
    def is_production(self):
        """Check if running in production mode"""
        return self.environment.lower() == 'production'

    def get_url(self, service_type):
        """
        Get API URL based on environment and service type

        Args:
            service_type (str): Type of service (MWALLET, CARD, STATUS_INQUIRY, REFUND)

        Returns:
            str: API endpoint URL
        """
        url_key = 'SANDBOX_URL' if self.is_sandbox else 'PRODUCTION_URL'
        urls = self.config.get(url_key, {})
        return urls.get(service_type, '')

    @property
    def mwallet_url(self):
        """Get MWallet API URL"""
        return self.get_url('MWALLET')

    @property
    def card_url(self):
        """Get Card Payment URL"""
        return self.get_url('CARD')

    @property
    def status_inquiry_url(self):
        """Get Status Inquiry URL"""
        return self.get_url('STATUS_INQUIRY')

    @property
    def refund_url(self):
        """Get Refund URL"""
        return self.get_url('REFUND')

    def is_configured(self):
        """Check if JazzCash is properly configured"""
        return all([
            self.merchant_id,
            self.password,
            self.integrity_salt,
        ])

    def get_summary(self):
        """Get configuration summary for debugging"""
        return {
            'merchant_id': self.merchant_id[:5] + '***' if self.merchant_id else 'Not Set',
            'password': '***' if self.password else 'Not Set',
            'integrity_salt': '***' if self.integrity_salt else 'Not Set',
            'environment': self.environment,
            'return_url': self.return_url,
            'ipn_url': self.ipn_url,
            'is_configured': self.is_configured(),
        }


# Global instance
jazzcash_config = JazzCashConfig()
