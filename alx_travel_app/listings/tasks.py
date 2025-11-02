"""
Celery tasks for background processing
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_payment_confirmation_email(payment_id):
    """
    Send payment confirmation email to user
    
    Args:
        payment_id: UUID of the payment
    """
    try:
        from .models import Payment
        
        payment = Payment.objects.select_related(
            'booking', 'booking__user', 'booking__property'
        ).get(payment_id=payment_id)
        
        user = payment.booking.user
        booking = payment.booking
        
        subject = f'Payment Confirmation - Booking #{booking.booking_id}'
        
        # Create HTML email content
        html_message = f"""
        <html>
        <body>
            <h2>Payment Confirmed!</h2>
            <p>Dear {user.first_name} {user.last_name},</p>
            <p>Your payment has been successfully processed.</p>
            
            <h3>Booking Details:</h3>
            <ul>
                <li><strong>Property:</strong> {booking.property.name}</li>
                <li><strong>Location:</strong> {booking.property.location}</li>
                <li><strong>Check-in:</strong> {booking.start_date}</li>
                <li><strong>Check-out:</strong> {booking.end_date}</li>
                <li><strong>Duration:</strong> {booking.duration_days} nights</li>
            </ul>
            
            <h3>Payment Details:</h3>
            <ul>
                <li><strong>Amount Paid:</strong> {payment.currency} {payment.amount}</li>
                <li><strong>Transaction ID:</strong> {payment.transaction_id}</li>
                <li><strong>Payment Date:</strong> {payment.payment_date.strftime('%Y-%m-%d %H:%M')}</li>
            </ul>
            
            <p>Thank you for choosing our service!</p>
            <p>Best regards,<br>ALX Travel Team</p>
        </body>
        </html>
        """
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Payment confirmation email sent to {user.email}")
        return f"Email sent to {user.email}"
        
    except Exception as e:
        logger.error(f"Error sending payment confirmation email: {str(e)}")
        raise


@shared_task
def send_booking_confirmation_email(booking_id):
    """
    Send booking confirmation email to user
    
    Args:
        booking_id: UUID of the booking
    """
    try:
        from .models import Booking
        
        booking = Booking.objects.select_related(
            'user', 'property', 'property__host'
        ).get(booking_id=booking_id)
        
        user = booking.user
        
        subject = f'Booking Confirmed - {booking.property.name}'
        
        html_message = f"""
        <html>
        <body>
            <h2>Booking Confirmed!</h2>
            <p>Dear {user.first_name} {user.last_name},</p>
            <p>Your booking has been confirmed by the host.</p>
            
            <h3>Booking Details:</h3>
            <ul>
                <li><strong>Property:</strong> {booking.property.name}</li>
                <li><strong>Location:</strong> {booking.property.location}</li>
                <li><strong>Check-in:</strong> {booking.start_date}</li>
                <li><strong>Check-out:</strong> {booking.end_date}</li>
                <li><strong>Total Price:</strong> ETB {booking.total_price}</li>
            </ul>
            
            <h3>Host Information:</h3>
            <ul>
                <li><strong>Name:</strong> {booking.property.host.first_name} {booking.property.host.last_name}</li>
                <li><strong>Email:</strong> {booking.property.host.email}</li>
                <li><strong>Phone:</strong> {booking.property.host.phone_number or 'N/A'}</li>
            </ul>
            
            <p>We hope you have a wonderful stay!</p>
            <p>Best regards,<br>ALX Travel Team</p>
        </body>
        </html>
        """
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Booking confirmation email sent to {user.email}")
        return f"Email sent to {user.email}"
        
    except Exception as e:
        logger.error(f"Error sending booking confirmation email: {str(e)}")
        raise


@shared_task
def send_payment_failed_email(payment_id):
    """
    Send payment failed notification email to user
    
    Args:
        payment_id: UUID of the payment
    """
    try:
        from .models import Payment
        
        payment = Payment.objects.select_related(
            'booking', 'booking__user'
        ).get(payment_id=payment_id)
        
        user = payment.booking.user
        
        subject = 'Payment Failed - Action Required'
        
        html_message = f"""
        <html>
        <body>
            <h2>Payment Failed</h2>
            <p>Dear {user.first_name} {user.last_name},</p>
            <p>Unfortunately, your payment could not be processed.</p>
            
            <p><strong>Booking Reference:</strong> {payment.booking.booking_id}</p>
            <p><strong>Amount:</strong> {payment.currency} {payment.amount}</p>
            
            <p>Please try again or contact our support team for assistance.</p>
            
            <p>Best regards,<br>ALX Travel Team</p>
        </body>
        </html>
        """
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Payment failed email sent to {user.email}")
        return f"Email sent to {user.email}"
        
    except Exception as e:
        logger.error(f"Error sending payment failed email: {str(e)}")
        raise