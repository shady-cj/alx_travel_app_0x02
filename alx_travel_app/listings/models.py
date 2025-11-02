"""
Models for the listings app.
Based on the Airbnb database schema provided.
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Use email as username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        db_table = 'User'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class Listing(models.Model):
    """
    Property/Listing model representing rental properties
    """
    property_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='listings'
    )
    name = models.CharField(max_length=150)
    description = models.TextField()
    location = models.CharField(max_length=255)
    price_per_night = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Property'
        indexes = [
            models.Index(fields=['host']),
            models.Index(fields=['location']),
            models.Index(fields=['price_per_night']),
        ]

    def __str__(self):
        return f"{self.name} in {self.location}"

    @property
    def average_rating(self):
        """Calculate average rating from reviews"""
        reviews = self.reviews.all()
        if reviews:
            return sum(review.rating for review in reviews) / len(reviews)
        return 0


class BookingStatus(models.Model):
    """
    Lookup table for booking statuses
    """
    status_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status_name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'BookingStatus'

    def __str__(self):
        return self.status_name


class Booking(models.Model):
    """
    Booking model representing property reservations
    """
    booking_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    status = models.ForeignKey(
        BookingStatus,
        on_delete=models.PROTECT,
        related_name='bookings'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Booking'
        indexes = [
            models.Index(fields=['property']),
            models.Index(fields=['user']),
            models.Index(fields=['start_date', 'end_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gt=models.F('start_date')),
                name='booking_end_after_start'
            )
        ]

    def __str__(self):
        return f"Booking {self.booking_id} - {self.property.name}"

    @property
    def duration_days(self):
        """Calculate booking duration in days"""
        return (self.end_date - self.start_date).days

    def clean(self):
        """Custom validation"""
        from django.core.exceptions import ValidationError
        if self.end_date <= self.start_date:
            raise ValidationError('End date must be after start date')


class Review(models.Model):
    """
    Review model for property reviews
    """
    review_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Review'
        indexes = [
            models.Index(fields=['property']),
            models.Index(fields=['user']),
            models.Index(fields=['rating']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['property', 'user'],
                name='unique_user_property_review'
            )
        ]

    def __str__(self):
        return f"Review by {self.user.first_name} for {self.property.name} - {self.rating}/5"


class PaymentMethod(models.Model):
    """
    Lookup table for payment methods
    """
    method_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    method_name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'PaymentMethod'

    def __str__(self):
        return self.method_name


class Payment(models.Model):
    """
    Payment model for booking payments with Chapa integration
    """
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    chapa_reference = models.CharField(max_length=255, unique=True, null=True, blank=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    updated_at = models.DateTimeField(auto_now=True)

    # Additional Chapa fields
    currency = models.CharField(max_length=3, default='ETB')  # Ethiopian Birr
    customer_email = models.EmailField()
    customer_first_name = models.CharField(max_length=100)
    customer_last_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = 'Payment'
        indexes = [
            models.Index(fields=['booking']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['chapa_reference']),
        ]

    def __str__(self):
        return f"Payment {self.payment_id} - {self.payment_status} - ${self.amount}"

    @property
    def is_successful(self):
        """Check if payment is successful"""
        return self.payment_status == 'completed'


class Message(models.Model):
    """
    Message model for user communications
    """
    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )
    message_body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Message'
        indexes = [
            models.Index(fields=['sender']),
            models.Index(fields=['recipient']),
            models.Index(fields=['sent_at']),
        ]

    def __str__(self):
        return f"Message from {self.sender.first_name} to {self.recipient.first_name}"