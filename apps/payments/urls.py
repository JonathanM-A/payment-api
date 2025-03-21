from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewset

router = DefaultRouter()
router.register(r"payments", PaymentViewset)


urlpatterns=[
    path("", include(router.urls))
]