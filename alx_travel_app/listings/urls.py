from django.urls import path, include
from rest_framework import routers
from .views import ListingViewset, BookingViewSet

router = routers.DefaultRouter()
router.register('listings', ListingViewSet, basename='listing')
router.register('bookings', BookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls))
]
