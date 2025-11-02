from django.db import models
import uuid
from django.utils import timezone
from django.db.models import Q, F

# Create your models here.

BOOKING_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('canceled', 'Canceled')
    ]
class Location(models.Model):
    location_id = models.UUIDField(
            primary_key=True,
            default=uuid.uuid4,
            editable=False
        )
    city = models.CharField(
            max_length=100,
            null=False
        )
    state = models.CharField(
            max_length=100,
            null=False
        )
    country = models.CharField(
            max_length=100,
            null=False
        )

    def __str__(self):
        return self.city


class Listing(models.Model):
    property_id = models.UUIDField(
            primary_key=True,
            default=uuid.uuid4,
            editable=False
        )
    host_id = models.ForeignKey(
            'user',
            on_delete=models.CASCADE,
            related_name='listings',
            null=False,
            db_index=True
        )
    name = models.CharField(
            max_length=200,
            null=False
        )
    description = models.TextField()
    location_id = models.ForeignKey(
            'location',
            on_delete=models.CASCADE,
            db_index=True
        )
    price_per_night = models.DecimalField(
            max_digits=10,
            decimal_places=2
        )
    created_at = models.DateFieldTime(auto_now_add=True)
    updated_at = models.DateFieldTime(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.host_id_username}"


class booking(models.Model):
    booking_id = models.UUIDField(
            primary_key=True,
            default=uuid.uuid4,
            editable=False
        )
    user_id = models.ForeignKey(
            'user',
            on_delete=models.CASCADE,
            related_name='booking',
            null=False,
            db_index=True
        )
    property_id = models.ForeignKey(
            'listing',
            on_delete=models.CASCADE,
            related_name='booking',
            null=False,
            db_index=True
        )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(
            max_length=200,
            null=False,
            choices=BOOKING_STATUS
        )

    def __str__(self):
        return f"By {self.user_id.username} for {self.property_id.name}"

    class Meta:
        constraints = [
                models.CheckConstraint(
                    check=Q(end_date__gt=F('start_date')),
                    name="end_date_gt_start_date"
                ),
                models.CheckConstraint(
                    check=Q(start_date__gte=timezone.now()),
                    name="start_date_gte_now"
                ),
            ]


class Review(models.Model):
    review_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property_id = models.ForeignKey('listings', on_delete=models.CASCADE, related_name='reviews', null=False, db_index=True)
    user_id = models.ForeignKey('user', on_delete=models.CASCADE, related_name='reviews', null=False, db_index=True)
    rating = models.PositiveSmallIntegerField(null=False)
    comment = models.TextField(null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(rating__gte=1),
                name="rating_non_negative"
            ),
            models.CheckConstraint(
                check=Q(rating__lte=5),
                name="rating_not_gt_5"
            )
        ]

    def __str__(self):
        return f'"{self.comment}" -{self.user_id.username}'


class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
    )

    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    booking_reference = models.CharField(max_length=100, unique=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='NGN')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.booking_reference} ({self.status})"
