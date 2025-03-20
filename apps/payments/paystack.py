from django.conf import settings
import requests


class Paystack:
    PAYSTACK_SK = settings.PAYSTACK_SECRET_KEY
    base_url = "https://api.paystack.co/"

    @classmethod
    def initialize_payment(cls, ref, email, amount, *args, **kwargs):
        path = f"transaction/initialize"
        headers = {
            "Authorization": f"Bearer {Paystack.PAYSTACK_SK}",
            "Content-Type": "application/json",
        }
        data = {"reference": ref, "email": email, "amount": amount}
        url = Paystack.base_url + path

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

            response_data = response.json()
            return response_data

        except requests.exceptions.RequestException as e:
            return False, str(e)

    @classmethod
    def verify_payment(cls, ref, *args, **kwargs):
        path = f"transaction/verify/{ref}"
        headers = {
            "Authorization": f"Bearer {Paystack.PAYSTACK_SK}",
            "Content-Type": "application/json",
        }
        url = Paystack.base_url + path

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            response_data = response.json()
            verification_status = response_data.get("status")
            message = response_data.get("message")
            data = response_data.get("data")
            payment_status = data.get("status")
            paid_at = data.get("paid_at")
            


            return verification_status, message, payment_status, paid_at

        except requests.exceptions.RequestException as e:
            return False, str(e)
