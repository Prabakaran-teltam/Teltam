import base64
import json
import hashlib
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class PhonePeClient:
    def __init__(self):
        self.merchant_id = getattr(settings, 'PHONEPE_MERCHANT_ID', 'PGTESTPAYUAT')
        self.salt_key = getattr(settings, 'PHONEPE_SALT_KEY', '099eb0cd-02cf-4e2a-8aca-3e6c6aff0399')
        self.salt_index = str(getattr(settings, 'PHONEPE_SALT_INDEX', 1))
        self.base_url = getattr(settings, 'PHONEPE_BASE_URL', 'https://api-preprod.phonepe.com/apis/pg-sandbox')
        self.callback_url = getattr(settings, 'PHONEPE_CALLBACK_URL', '')
        self.redirect_url = getattr(settings, 'PHONEPE_REDIRECT_URL', '')

    def _generate_checksum(self, payload_b64, endpoint):
        """
        Generate PhonePe X-VERIFY checksum.
        Formula: SHA256(base64Payload + endpoint + saltKey) + "###" + saltIndex
        """
        checksum_str = payload_b64 + endpoint + self.salt_key
        sha256_hash = hashlib.sha256(checksum_str.encode('utf-8')).hexdigest()
        return f"{sha256_hash}###{self.salt_index}"

    def initiate_payment(self, merchant_transaction_id, merchant_user_id, amount_in_rupees, plan_slug, mobile_number=None):
        """
        Initiates a payment by making a request to PhonePe standard pay API (/pg/v1/pay).
        Amount in rupees is converted to paise.
        """
        endpoint = "/pg/v1/pay"
        url = f"{self.base_url}{endpoint}"

        # Convert amount to paise
        amount_paise = int(float(amount_in_rupees) * 100)

        # Dynamic callback and redirect URLs
        # In checkout we redirect/callback with transaction details
        payload = {
            "merchantId": self.merchant_id,
            "merchantTransactionId": merchant_transaction_id,
            "merchantUserId": merchant_user_id,
            "amount": amount_paise,
            "redirectUrl": self.redirect_url,
            "redirectMode": "REDIRECT", # Or POST/GET. Standard checkout uses REDIRECT
            "callbackUrl": self.callback_url,
            "paymentInstrument": {
                "type": "PAY_PAGE"
            }
        }

        if mobile_number:
            payload["mobileNumber"] = str(mobile_number)

        # Base64 encode the JSON payload
        payload_json = json.dumps(payload)
        payload_b64 = base64.b64encode(payload_json.encode('utf-8')).decode('utf-8')

        # Generate X-VERIFY checksum
        x_verify = self._generate_checksum(payload_b64, endpoint)

        headers = {
            "Content-Type": "application/json",
            "X-VERIFY": x_verify,
            "accept": "application/json"
        }

        request_body = {
            "request": payload_b64
        }

        logger.info(f"Initiating PhonePe payment for Txn: {merchant_transaction_id}, Amount: {amount_paise} paise")

        try:
            response = requests.post(url, json=request_body, headers=headers, timeout=30)
            response_json = response.json()
            return response_json, payload_json
        except Exception as e:
            logger.error(f"Error initiating payment with PhonePe: {str(e)}")
            return {"success": False, "message": str(e)}, payload_json

    def check_payment_status(self, merchant_transaction_id):
        """
        Checks status of a transaction using PhonePe Status Check API (/pg/v1/status/{merchantId}/{merchantTransactionId}).
        """
        endpoint = f"/pg/v1/status/{self.merchant_id}/{merchant_transaction_id}"
        url = f"{self.base_url}{endpoint}"

        # Checksum calculation: SHA256(endpoint + saltKey) + "###" + saltIndex
        checksum_str = endpoint + self.salt_key
        sha256_hash = hashlib.sha256(checksum_str.encode('utf-8')).hexdigest()
        x_verify = f"{sha256_hash}###{self.salt_index}"

        headers = {
            "Content-Type": "application/json",
            "X-VERIFY": x_verify,
            "X-MERCHANT-ID": self.merchant_id,
            "accept": "application/json"
        }

        logger.info(f"Checking PhonePe payment status for Txn: {merchant_transaction_id}")

        try:
            response = requests.get(url, headers=headers, timeout=30)
            return response.json()
        except Exception as e:
            logger.error(f"Error checking payment status from PhonePe: {str(e)}")
            return {"success": False, "message": str(e)}

    def verify_webhook_signature(self, x_verify_header, response_b64):
        """
        Verifies the PhonePe S2S callback signature.
        Formula: SHA256(response_b64 + saltKey) + "###" + saltIndex
        """
        if not x_verify_header or not response_b64:
            return False
        
        checksum_str = response_b64 + self.salt_key
        sha256_hash = hashlib.sha256(checksum_str.encode('utf-8')).hexdigest()
        computed_verify = f"{sha256_hash}###{self.salt_index}"
        
        return computed_verify == x_verify_header
