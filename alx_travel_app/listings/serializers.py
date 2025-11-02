from rest_framework import serializers
from .model import Location, Listing, Booking, Review


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['location_id', 'city', 'state', 'country']


class ListingSerializer(serializer.ModelSerializer):
    location = LocationSerializer(read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(
            queryset=Location.objects.all(),
            write_only=True
        )

    class Meta:
        model = Listing
        fields = [
                'property_id', 'host_id', 'name', 'description',
                'location', 'location_id', 'price_per_night',
                'created_at', 'updated_at'
            ]
        read_only_fields = ['property_id', 'created_at', 'updated_at', 'host_id']

    def create(self, validated_data):
        #Host will be sef from context or view
        return Listing.objects.creat(**validated_data)


class BookingSerializer(serializers.ModelSerializer):
    property = ListingSerializer(read_only=True, source='property_id')
    property_id = serializers.PrimaryKeyRelatedField(
            queryset=Listing.objects.all(),
            write_only=True
        )
    user = serializers.StringRelatedField(read_only=True, source='user_id')

    class Meta:
        model = booking
        fields = [
                'booking_id', 'property', 'property_id', 'user', 'user_id',
                'start_date', 'end_date', 'status', 'created_at'
            ]

    def create(self, validated_data):
        #user is injected from context or view
        return Booking.objects.create(**validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True, source='user_id')
    property = ListingsSerializer(read_only=True, source='property_id')
    property_id = serializers.PrimaryKeyRelatedField(
        queryset=Listings.objects.all(),
        write_only=True
    )

    class Meta:
        model = Review
        fields = [
            'review_id', 'property', 'property_id', 'user', 'user_id',
            'rating', 'comment', 'created_at'
        ]
        read_only_fields = ['review_id', 'created_at', 'user', 'user_id']

    def create(self, validated_data):
        # TODO: User is injected from context or view
        return Review.objects.create(**validated_data)
