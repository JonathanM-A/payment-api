import unittest
from unittest.mock import patch
from django.test import TestCase, RequestFactory
from django.test import TestCase
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework import status
from rest_framework.test import APIClient
from .paystack import Paystack
from .views import PaymentViewset
from .models import Payment, PaymentStatus
from .serializers import PaymentSerializer


class PaystackAPITest(TestCase):
    @patch("requests.post")
    def test_initialize_payment_success(self, mock_post):
        """Test successful payment initialization."""
        # Mock the Paystack API response
        mock_response = {
            "status": True,
            "data": {"authorization_url": "https://paystack.com/authorize"},
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        # Call the method
        status, data = Paystack.initialize_payment("ref123", "john@example.com", 5000)

        # Assertions
        self.assertTrue(status)
        self.assertEqual(data["authorization_url"], "https://paystack.com/authorize")
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_initialize_payment_failure(self, mock_post):
        """Test failed payment initialization."""
        # Mock the Paystack API response
        mock_post.side_effect = Exception("API request failed")

        # Call the method
        status, data = Paystack.initialize_payment("ref123", "john@example.com", 5000)

        # Assertions
        self.assertFalse(status)
        self.assertEqual(data, "API request failed")

    @patch("requests.get")
    def test_verify_payment_success(self, mock_get):
        """Test successful payment verification."""
        # Mock the Paystack API response
        mock_response = {
            "status": True,
            "data": {"status": "success", "amount": 500000},  # Amount in kobo
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        # Call the method
        status, data = Paystack.verify_payment("ref123")

        # Assertions
        self.assertTrue(status)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["amount"], 500000)
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_verify_payment_failure(self, mock_get):
        """Test failed payment verification."""
        # Mock the Paystack API response
        mock_get.side_effect = Exception("API request failed")

        # Call the method
        status, data = Paystack.verify_payment("ref123")

        # Assertions
        self.assertFalse(status)
        self.assertEqual(data, "API request failed")


class PaymentModelTest(TestCase):
    def setUp(self):
        # Create a sample payment for testing
        self.payment = Payment.objects.create(
            name="John Doe",
            email="john@example.com",
            amount=5000,
        )

    def test_payment_creation(self):
        """Test that a payment instance is created successfully."""
        self.assertEqual(self.payment.name, "John Doe")
        self.assertEqual(self.payment.email, "john@example.com")
        self.assertEqual(self.payment.amount, 5000)
        self.assertEqual(self.payment.status, PaymentStatus.PENDING)
        self.assertIsNotNone(self.payment.ref)
        self.assertIsNone(self.payment.payment_date)

    def test_ref_generation_on_save(self):
        """Test that a unique reference is generated when saving the payment."""
        self.assertIsNotNone(self.payment.ref)
        self.assertTrue(len(self.payment.ref) > 0)

    def test_ref_uniqueness(self):
        """Test that the generated reference is unique."""
        ref = self.payment.ref
        new_payment = Payment(
            name="Jane Doe",
            email="jane@example.com",
            amount=3000,
        )
        new_payment.save()
        self.assertNotEqual(new_payment.ref, ref)

    def test_amount_value_method(self):
        """Test the `amount_value` method converts amount to kobo."""
        self.assertEqual(self.payment.amount_value(), 5000 * 100)

    def test_minimum_amount_validation(self):
        """Test that the amount cannot be less than 0."""
        with self.assertRaises(ValidationError):
            payment = Payment(
                name="Invalid Amount",
                email="invalid@example.com",
                amount=-100,
            )
            payment.full_clean()  # Trigger validation

    def test_verify_payment_success(self):
        """Test the `verify_payment` method for a successful payment."""

        # Mock the Paystack verification response
        class MockPaystack:
            def verify_payment(self, ref):
                return True, {
                    "status": "success",
                    "amount": self.payment.amount_value(),
                }

        # Replace the Paystack class with the mock
        self.payment.verify_payment = lambda: Payment.verify_payment(
            self.payment, MockPaystack()
        )

        # Verify the payment
        result = self.payment.verify_payment()

        # Assertions
        self.assertTrue(result)
        self.assertEqual(self.payment.status, PaymentStatus.SUCCESS)
        self.assertIsNotNone(self.payment.payment_date)

    def test_verify_payment_failed(self):
        """Test the `verify_payment` method for a failed payment."""

        # Mock the Paystack verification response
        class MockPaystack:
            def verify_payment(self, ref):
                return False, "Payment verification failed"

        # Replace the Paystack class with the mock
        self.payment.verify_payment = lambda: Payment.verify_payment(
            self.payment, MockPaystack()
        )

        # Verify the payment
        result = self.payment.verify_payment()

        # Assertions
        self.assertFalse(result)
        self.assertEqual(self.payment.status, PaymentStatus.FAILED)
        self.assertIsNone(self.payment.payment_date)

    def test_verify_payment_amount_mismatch(self):
        """Test the `verify_payment` method when the amount does not match."""

        # Mock the Paystack verification response
        class MockPaystack:
            def verify_payment(self, ref):
                return True, {
                    "status": "success",
                    "amount": self.payment.amount_value() + 1000,  # Mismatched amount
                }

        # Replace the Paystack class with the mock
        self.payment.verify_payment = lambda: Payment.verify_payment(
            self.payment, MockPaystack()
        )

        # Verify the payment
        result = self.payment.verify_payment()

        # Assertions
        self.assertFalse(result)
        self.assertEqual(self.payment.status, PaymentStatus.FAILED)
        self.assertIsNone(self.payment.payment_date)

    def test_str_representation(self):
        """Test the string representation of the Payment model."""
        self.assertEqual(
            str(self.payment), f"{self.payment.name} - {self.payment.amount_value()}"
        )


class PaymentInitializeViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = RequestFactory()
        self.payment = Payment.objects.create(
            name="John Doe",
            email="john@example.com",
            amount=5000,  # Amount in kobo (e.g., 5000 = ₦50.00)
        )
        self.view = PaymentViewset.as_view({"get": "retrieve"})

    def test_retrieve_payment_details(self):
        """Test retrieving payment details and verifying the payment."""

        # Mock the Paystack verification response
        class MockPaystack:
            def verify_payment(self, ref):
                return True, {
                    "status": "success",
                    "amount": self.payment.amount_value(),
                }

        # Replace the Paystack class with the mock
        self.payment.verify_payment = lambda: Payment.verify_payment(
            self.payment, MockPaystack()
        )

        # Make a GET request to retrieve payment details
        request = self.factory.get(f"/payments/{self.payment.id}/")
        response = self.view(request, pk=self.payment.id)

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], 200)
        self.assertEqual(
            response.data["message"], "Payment details retrieved successfully"
        )
        self.assertEqual(response.data["payment"]["id"], self.payment.id)
        self.assertEqual(response.data["payment"]["customer_name"], "John Doe")
        self.assertEqual(response.data["payment"]["customer_email"], "john@example.com")
        self.assertEqual(
            response.data["payment"]["amount"], self.payment.amount_value()
        )
        self.assertEqual(response.data["payment"]["status"], "success")

    def test_retrieve_payment_details_failed_verification(self):
        """Test retrieving payment details when verification fails."""

        # Mock the Paystack verification response
        class MockPaystack:
            def verify_payment(self, ref):
                return False, "Payment verification failed"

        # Replace the Paystack class with the mock
        self.payment.verify_payment = lambda: Payment.verify_payment(
            self.payment, MockPaystack()
        )

        # Make a GET request to retrieve payment details
        request = self.factory.get(f"/payments/{self.payment.id}/")
        response = self.view(request, pk=self.payment.id)

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], 200)
        self.assertEqual(
            response.data["message"], "Payment details retrieved successfully"
        )
        self.assertEqual(response.data["payment"]["status"], "failed")


class PaymentSerializerTest(TestCase):
    def setUp(self):
        self.payment = Payment.objects.create(
            name="John Doe",
            email="john@example.com",
            amount=5000,  # Amount in kobo (e.g., 5000 = ₦50.00)
        )

    def test_serializer_representation(self):
        """Test the serializer's `to_representation` method."""
        serializer = PaymentSerializer(self.payment)
        expected_data = {
            "payment": {
                "id": self.payment.id,
                "customer_name": "John Doe",
                "customer_email": "john@example.com",
                "amount": self.payment.amount_value(),
                "status": "pending",
            }
        }
        self.assertEqual(serializer.data, expected_data)

    def test_get_payment_url_success(self):
        """Test the `get_payment_url` method for a successful payment initialization."""

        # Mock the Paystack initialization response
        class MockPaystack:
            def initialize_payment(self, ref, email, amount):
                return True, {"authorization_url": "https://paystack.com/authorize"}

        # Replace the Paystack class with the mock
        Paystack.initialize_payment = MockPaystack().initialize_payment

        serializer = PaymentSerializer(self.payment)
        payment_url = serializer.get_payment_url(self.payment)

        # Assertions
        self.assertEqual(
            payment_url, {"Authorization url": "https://paystack.com/authorize"}
        )

    def test_get_payment_url_failure(self):
        """Test the `get_payment_url` method for a failed payment initialization."""

        # Mock the Paystack initialization response
        class MockPaystack:
            def initialize_payment(self, ref, email, amount):
                return False, "Payment initialization failed"

        # Replace the Paystack class with the mock
        Paystack.initialize_payment = MockPaystack().initialize_payment

        serializer = PaymentSerializer(self.payment)
        with self.assertRaises(serializers.ValidationError) as context:
            serializer.get_payment_url(self.payment)

        # Assertions
        self.assertEqual(
            str(context.exception.detail["payment_url"]),
            "Payment initialization failed",
        )
