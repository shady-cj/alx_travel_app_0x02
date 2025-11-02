"""
Serializers for the listings app.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Listing, Booking, Review, BookingStatus, Payment, PaymentMethod, Message

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model
    """
    class Meta:
        model = User
        fields = ['user_id', 'first_name', 'last_name', 'email', 'phone_number', 'created_at']
        read_only_fields = ['user_id', 'created_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username', 'phone_number', 'password', 'password_confirm']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class ReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for Review model
    """
    user = UserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ['review_id', 'user', 'rating', 'comment', 'created_at']
        read_only_fields = ['review_id', 'created_at']


class ListingSerializer(serializers.ModelSerializer):
    """
    Serializer for Listing model
    """
    host = UserSerializer(read_only=True)
    average_rating = serializers.ReadOnlyField()
    reviews_count = serializers.SerializerMethodField()
    reviews = ReviewSerializer(many=True, read_only=True)

    class Meta:
        model = Listing
        fields = [
            'property_id', 'host', 'name', 'description', 'location', 
            'price_per_night', 'average_rating', 'reviews_count', 'reviews',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['property_id', 'created_at', 'updated_at']

    def get_reviews_count(self, obj):
        return obj.reviews.count()


class ListingCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating listings
    """
    class Meta:
        model = Listing
        fields = ['name', 'description', 'location', 'price_per_night']

    def validate_price_per_night(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price per night must be greater than 0")
        return value


class BookingStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for BookingStatus model
    """
    class Meta:
        model = BookingStatus
        fields = ['status_id', 'status_name']
        read_only_fields = ['status_id']


class BookingSerializer(serializers.ModelSerializer):
    """
    Serializer for Booking model
    """
    user = UserSerializer(read_only=True)
    property = ListingSerializer(read_only=True)
    status = BookingStatusSerializer(read_only=True)
    duration_days = serializers.ReadOnlyField()

    class Meta:
        model = Booking
        fields = [
            'booking_id', 'property', 'user', 'start_date', 'end_date',
            'total_price', 'status', 'duration_days', 'created_at'
        ]
        read_only_fields = ['booking_id', 'created_at']


class BookingCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating bookings
    """
    property_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = Booking
        fields = ['property_id', 'start_date', 'end_date']

    def validate(self, attrs):
        """
        Custom validation for booking dates and availability
        """
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        property_id = attrs.get('property_id')

        # Validate dates
        if end_date <= start_date:
            raise serializers.ValidationError("End date must be after start date")

        # Check if property exists
        try:
            property_obj = Listing.objects.get(property_id=property_id)
        except Listing.DoesNotExist:
            raise serializers.ValidationError("Property not found")

        # Check for overlapping bookings
        overlapping_bookings = Booking.objects.filter(
            property=property_obj,
            start_date__lt=end_date,
            end_date__gt=start_date
        ).exclude(
            status__status_name__in=['cancelled', 'rejected']
        )

        if overlapping_bookings.exists():
            raise serializers.ValidationError("Property is not available for the selected dates")

        attrs['property'] = property_obj
        return attrs

    def create(self, validated_data):
        property_obj = validated_data.pop('property')
        validated_data.pop('property_id')
        
        # Calculate total price
        duration = (validated_data['end_date'] - validated_data['start_date']).days
        total_price = property_obj.price_per_night * duration
        validated_data['total_price'] = total_price
        validated_data['property'] = property_obj

        # Set default status (you might want to create this status first)
        default_status, _ = BookingStatus.objects.get_or_create(status_name='pending')
        validated_data['status'] = default_status

        return super().create(validated_data)


class PaymentMethodSerializer(serializers.ModelSerializer):
    """
    Serializer for PaymentMethod model
    """
    class Meta:
        model = PaymentMethod
        fields = ['method_id', 'method_name']
        read_only_fields = ['method_id']


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for Payment model
    """
    booking = BookingSerializer(read_only=True)
    payment_method = PaymentMethodSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = ['payment_id', 'booking', 'amount', 'payment_date', 'payment_method']
        read_only_fields = ['payment_id', 'payment_date']


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for Message model
    """
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['message_id', 'sender', 'recipient', 'message_body', 'sent_at']
        read_only_fields = ['message_id', 'sent_at']


class MessageCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating messages
    """
    recipient_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Message
        fields = ['recipient_id', 'message_body']

    def validate_recipient_id(self, value):
        try:
            recipient = User.objects.get(user_id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Recipient not found")
        return value

    def create(self, validated_data):
        recipient_id = validated_data.pop('recipient_id')
        recipient = User.objects.get(user_id=recipient_id)
        validated_data['recipient'] = recipient
        return super().create(validated_data)