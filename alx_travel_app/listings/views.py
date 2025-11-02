from django.shortcuts import render
from .models import CustomUser, Listing, Booking, Review, Payment
import os
from django.conf import settings
from rest_framework import viewsets, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
import requests
import logging
from decimal import Decimal, InvalidOperation
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import (CustomUserSerializer,
                          ListingSerializer, 
                          BookingSerializer, 
                          ReviewSerializer, 
                          PaymentSerializer
)


# Create your views here.
class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all() 
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_permissions(self):
        if self.action in ['create']:  
            return [AllowAny()]
        return [IsAuthenticated()]


class ListingViewSet(viewsets.ModelViewSet):
    """
    Manages Listing views
    """

    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(host=self.request.user)

    
class BookingViewSet(viewsets.ModelViewSet):
    """
    Manages Bookings views
    """
    
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
       

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
       

class InitializePaymentAPIView(APIView):
    """
    Initialize a payment with Chapa and store the transaction in your DB.
    """
    permission_classes = [permissions.IsAuthenticated]  # or AllowAny for testing

    def post(self, request, *args, **kwargs):
        from decimal import Decimal
        user = request.user if request.user.is_authenticated else None
        data = request.data

        amount = data.get("amount")
        email = data.get("email")
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        booking_reference = data.get("booking_reference") or f"BOOK-{int(time.time())}"
        currency = data.get("currency", "NGN")
        callback_url = data.get("callback_url") or f"{request.build_absolute_uri('/api/payments/verify/')}{booking_reference}/"

        if not (amount and email):
            return Response({"detail": "amount and email are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Create payment record locally
        payment = Payment.objects.create(
            user=user,
            booking_reference=booking_reference,
            amount=Decimal(amount),
            currency=currency,
            status="pending"
        )

        # Prepare Chapa API call
        chapa_url = "https://api.chapa.co/v1/transaction/initialize"
        headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}"}
        payload = {
            "amount": str(amount),
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "tx_ref": booking_reference,
            "currency": currency,
            "callback_url": callback_url,
            "customization": {
                "title": "ALX Travel Payment",
                "description": "Payment for booking"
            }
        }

        try:
            resp = requests.post(chapa_url, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            resp_data = resp.json()
        except requests.RequestException as e:
            payment.status = "failed"
            payment.save()
            return Response({"detail": "Failed to initiate payment", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        if resp_data.get("status") == "success":
            checkout_url = resp_data.get("data", {}).get("checkout_url")
            # Optionally store full Chapa response for debugging
            if hasattr(payment, "metadata"):
                payment.metadata = resp_data
                payment.save()

            return Response({
                "detail": "Payment initialized successfully",
                "checkout_url": checkout_url,
                "payment": PaymentSerializer(payment).data
            }, status=status.HTTP_201_CREATED)
        else:
            payment.status = "failed"
            payment.save()
            return Response({"detail": "Chapa initialization failed", "response": resp_data}, status=status.HTTP_400_BAD_REQUEST)


CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY")
CHAPA_VERIFY_URL = "https://api.chapa.co/v1/transaction/verify/"

logger = logging.getLogger(__name__)
class VerifyPaymentAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, tx_ref=None, *args, **kwargs):
        tx_ref = tx_ref or request.query_params.get("tx_ref")
        if not tx_ref:
            return Response({"detail": "tx_ref is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Find local payment record
        try:
            payment = Payment.objects.get(booking_reference=tx_ref)
        except Payment.DoesNotExist:
            return Response({"detail": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        # If already successful, return current state (idempotent)
        if payment.status == "successful":
            return Response({"detail": "Payment already successful", "payment": PaymentSerializer(payment).data})

        if not CHAPA_SECRET_KEY:
            logger.error("CHAPA_SECRET_KEY not configured")
            return Response({"detail": "Payment gateway not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        verify_url = f"{CHAPA_VERIFY_URL}{tx_ref}"
        headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}"}
        try:
            resp = requests.get(verify_url, headers=headers, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to call Chapa verify: %s", str(e))
            return Response({"detail": "Failed to verify with Chapa", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        # Parse JSON safely
        try:
            resp_data = resp.json()
        except ValueError:
            logger.error("Invalid JSON from Chapa: %s", resp.text)
            return Response({"detail": "Invalid response from payment provider"}, status=status.HTTP_502_BAD_GATEWAY)

        logger.info("Chapa verify response for %s: %s", tx_ref, resp.text)

        chapa_status = (resp_data.get("status") or "").lower()
        chapa_data = resp_data.get("data") or {}

        chapa_tx_ref = chapa_data.get("tx_ref") or chapa_data.get("reference") or chapa_data.get("id")
        chapa_amount = chapa_data.get("amount")

        # Basic checks
        if str(chapa_tx_ref) != str(payment.booking_reference):
            logger.warning("tx_ref mismatch: local=%s chapa=%s", payment.booking_reference, chapa_tx_ref)
            payment.status = "failed"
            # optional: payment.metadata = resp_data
            payment.save()
            return Response({"detail": "Transaction reference mismatch. Marked failed."}, status=status.HTTP_400_BAD_REQUEST)

        # Compare amounts (use Decimal)
        amount_ok = True
        if chapa_amount is not None:
            try:
                chapa_amount_dec = Decimal(str(chapa_amount))
                if chapa_amount_dec != payment.amount:
                    amount_ok = False
                    logger.warning("amount mismatch for %s: local=%s chapa=%s", tx_ref, payment.amount, chapa_amount_dec)
            except (InvalidOperation, TypeError) as e:
                logger.warning("Could not parse chapa amount: %s", e)
                amount_ok = False

        # Determine success — parenthesize properly
        message = (resp_data.get("message") or "").lower()
        success_by_message = "successful" in message or "success" in message
        chapa_data_status = (chapa_data.get("status") or "").lower()

        is_success = (chapa_status == "success") or (chapa_data_status in ("success", "completed")) or success_by_message

        if is_success and amount_ok:
            payment.status = "successful"
            payment.transaction_id = chapa_data.get("reference") or chapa_data.get("id") or chapa_data.get("tx_ref") or payment.transaction_id
            payment.metadata = resp_data if hasattr(payment, "metadata") else None
            payment.save()
            # enqueue email
            try:
                from .tasks import send_payment_confirmation_email
                send_payment_confirmation_email.delay(payment.id)
            except Exception as e:
                logger.error("Failed to queue email task: %s", e)
            return Response({"detail": "Payment verified and marked successful", "payment": PaymentSerializer(payment).data})
        else:
            payment.status = "failed"
            payment.transaction_id = chapa_data.get("reference") or chapa_data.get("id") or chapa_data.get("tx_ref") or payment.transaction_id
            payment.metadata = resp_data if hasattr(payment, "metadata") else None
            payment.save()
            return Response({"detail": "Payment verification returned non-success state", "raw": resp_data, "payment": PaymentSerializer(payment).data},
                            status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name="dispatch")
class ChapaWebhookAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        payload = request.data or {}
        tx_ref = payload.get("tx_ref") or payload.get("reference")
        if not tx_ref:
            return Response({"detail": "tx_ref missing"}, status=status.HTTP_400_BAD_REQUEST)

        if not CHAPA_SECRET_KEY:
            logger.error("CHAPA_SECRET_KEY not configured")
            return Response({"detail": "Payment gateway not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        verify_url = f"{CHAPA_VERIFY_URL}{tx_ref}"
        headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}"}
        try:
            resp = requests.get(verify_url, headers=headers, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error("Webhook verify call failed: %s", e)
            return Response({"detail": "Failed to reach Chapa", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        try:
            resp_data = resp.json()
        except ValueError:
            logger.error("Invalid JSON in webhook verify response: %s", resp.text)
            return Response({"detail": "Invalid response from payment provider"}, status=status.HTTP_502_BAD_GATEWAY)

        logger.info("Chapa webhook verify response for %s: %s", tx_ref, resp.text)

        chapa_status = (resp_data.get("status") or "").lower()
        chapa_data = resp_data.get("data") or {}

        try:
            payment = Payment.objects.get(booking_reference=tx_ref)
        except Payment.DoesNotExist:
            logger.warning("Webhook received for unknown payment: %s", tx_ref)
            return Response({"detail": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        chapa_data_status = (chapa_data.get("status") or "").lower()
        is_success = (chapa_status == "success") or (chapa_data_status in ("success", "completed"))

        if is_success:
            if payment.status != "successful":
                payment.status = "successful"
                payment.transaction_id = chapa_data.get("reference") or chapa_data.get("id") or chapa_data.get("tx_ref") or payment.transaction_id
                payment.metadata = resp_data if hasattr(payment, "metadata") else None
                payment.save()
                try:
                    from .tasks import send_payment_confirmation_email
                    send_payment_confirmation_email.delay(payment.id)
                except Exception as e:
                    logger.error("Failed to queue email from webhook: %s", e)
            else:
                logger.info("Webhook: payment already marked successful: %s", tx_ref)

            return Response({"detail": "Updated to successful"})
        else:
            payment.status = "failed"
            payment.metadata = resp_data if hasattr(payment, "metadata") else None
            payment.save()
            return Response({"detail": "Updated to failed"}, status=status.HTTP_200_OK)
