import logging
from django.conf import settings
from phonepe.sdk.pg.payments.v2.standard_checkout_client import StandardCheckoutClient
from phonepe.sdk.pg.env import Env
from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import StandardCheckoutPayRequest

logger = logging.getLogger(__name__)

class PhonePeService:
    _instance = None

    @classmethod
    def get_client(cls):
        if cls._instance is None:
            client_id = getattr(settings, 'PHONEPE_CLIENT_ID', 'PGTESTPAYUAT')
            client_secret = getattr(settings, 'PHONEPE_CLIENT_SECRET', '099eb0cd-02cf-4e2a-8aca-3e6c6aff0399')
            client_version = int(getattr(settings, 'PHONEPE_CLIENT_VERSION', 1))
            env_str = getattr(settings, 'PHONEPE_ENV', 'SANDBOX').upper()
            env = Env.PRODUCTION if env_str == 'PRODUCTION' else Env.SANDBOX

            logger.info(f"Initializing PhonePe StandardCheckoutClient (Env: {env_str})")
            cls._instance = StandardCheckoutClient.get_instance(
                client_id=client_id,
                client_secret=client_secret,
                client_version=client_version,
                env=env
            )
        return cls._instance

    def initiate_payment(self, merchant_order_id, amount_in_rupees, redirect_url=None):
        """
        Initiates checkout payment by converting amount to paisa and invoking pay() on standard checkout client.
        """
        client = self.get_client()
        amount_paisa = int(float(amount_in_rupees) * 100)
        
        if not redirect_url:
            redirect_url = getattr(settings, 'PHONEPE_REDIRECT_URL', '')

        logger.info(f"Building pay request: Order ID={merchant_order_id}, Amount={amount_paisa} paisa, Redirect={redirect_url}")
        
        try:
            pay_request = StandardCheckoutPayRequest.build_request(
                merchant_order_id=merchant_order_id,
                amount=amount_paisa,
                redirect_url=redirect_url
            )
            response = client.pay(pay_request)
            return response
        except Exception as e:
            logger.exception(f"SDK failed to initiate payment for Order ID {merchant_order_id}: {str(e)}")
            raise e

    def get_payment_status(self, merchant_order_id):
        """
        Fetches payment order status using standard checkout status check API.
        """
        client = self.get_client()
        logger.info(f"Querying order status: Order ID={merchant_order_id}")
        
        try:
            # Setting details=True gets detailed attempt details
            response = client.get_order_status(merchant_order_id=merchant_order_id, details=True)
            return response
        except Exception as e:
            logger.exception(f"SDK failed to check payment status for Order ID {merchant_order_id}: {str(e)}")
            raise e

    def validate_callback(self, callback_header, callback_body):
        """
        Validates server-to-server callback authenticity using SDK's validate_callback.
        Uses Client ID and Client Secret as standard basicauth parameters.
        """
        client = self.get_client()
        username = getattr(settings, 'PHONEPE_CLIENT_ID', 'PGTESTPAYUAT')
        password = getattr(settings, 'PHONEPE_CLIENT_SECRET', '099eb0cd-02cf-4e2a-8aca-3e6c6aff0399')
        
        logger.info("Verifying callback notification via SDK validate_callback")
        try:
            callback_resp = client.validate_callback(
                username=username,
                password=password,
                callback_header_data=callback_header,
                callback_response_data=callback_body
            )
            return callback_resp
        except Exception as e:
            logger.exception(f"SDK failed to validate callback: {str(e)}")
            raise e
