"""
URL configuration for listings app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ListingViewSet, BookingViewSet, ReviewViewSet, UserViewSet,
    PaymentInitiateView, PaymentVerifyView, PaymentWebhookView,
    PaymentListView, PaymentDetailView
)

# Create a router for DRF viewsets
router = DefaultRouter()

# Register viewsets with the router
router.register(r'listings', ListingViewSet, basename='listing')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Payment endpoints
    path('payments/initiate/', PaymentInitiateView.as_view(), name='payment-initiate'),
    path('payments/verify/<str:tx_ref>/', PaymentVerifyView.as_view(), name='payment-verify'),
    path('payments/webhook/', PaymentWebhookView.as_view(), name='payment-webhook'),
    path('payments/', PaymentListView.as_view(), name='payment-list'),
    path('payments/<uuid:payment_id>/', PaymentDetailView.as_view(), name='payment-detail'),
]