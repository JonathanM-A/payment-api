from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "name",
            "email",
            "amount",
            "status",
            "paid_at"
        ]
        read_only_fields = ["status", "id", "paid_at"]
