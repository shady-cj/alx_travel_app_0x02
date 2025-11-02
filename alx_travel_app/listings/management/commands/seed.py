"""
Management command to seed the database with sample data.
"""
import random
from decimal import Decimal
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from listings.models import (
    Listing, Booking, Review, BookingStatus, 
    PaymentMethod, Payment, Message
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=20,
            help='Number of users to create (default: 20)',
        )
        parser.add_argument(
            '--listings',
            type=int,
            default=50,
            help='Number of listings to create (default: 50)',
        )
        parser.add_argument(
            '--bookings',
            type=int,
            default=100,
            help='Number of bookings to create (default: 100)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            self.clear_data()

        self.stdout.write('Starting database seeding...')

        with transaction.atomic():
            # Create lookup data first
            self.create_lookup_data()
            
            # Create users
            users = self.create_users(options['users'])
            
            # Create listings
            listings = self.create_listings(users, options['listings'])
            
            # Create bookings
            bookings = self.create_bookings(users, listings, options['bookings'])
            
            # Create reviews
            self.create_reviews(users, listings, bookings)
            
            # Create payments
            self.create_payments(bookings)
            
            # Create messages
            self.create_messages(users)

        self.stdout.write(
            self.style.SUCCESS('Successfully seeded the database!')
        )

    def clear_data(self):
        """Clear existing data"""
        models_to_clear = [
            Message, Payment, Review, Booking, Listing, User,
            PaymentMethod, BookingStatus
        ]
        
        for model in models_to_clear:
            count = model.objects.count()
            if count > 0:
                model.objects.all().delete()
                self.stdout.write(f'Cleared {count} {model.__name__} records')

    def create_lookup_data(self):
        """Create lookup table data"""
        self.stdout.write('Creating lookup data...')
        
        # Booking statuses
        statuses = ['pending', 'confirmed', 'cancelled', 'completed', 'rejected']
        for status in statuses:
            BookingStatus.objects.get_or_create(status_name=status)
        
        # Payment methods
        methods = ['credit_card', 'debit_card', 'paypal', 'bank_transfer', 'cash']
        for method in methods:
            PaymentMethod.objects.get_or_create(method_name=method)

    def create_users(self, count):
        """Create sample users"""
        self.stdout.write(f'Creating {count} users...')
        
        users = []
        first_names = [
            'John', 'Jane', 'Michael', 'Sarah', 'David', 'Emma', 'James', 'Emily',
            'Robert', 'Jessica', 'William', 'Ashley', 'Christopher', 'Amanda',
            'Matthew', 'Jennifer', 'Daniel', 'Melissa', 'Anthony', 'Lisa'
        ]
        
        last_names = [
            'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller',
            'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez',
            'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin'
        ]
        
        for i in range(count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            username = f"{first_name.lower()}{last_name.lower()}{i}"
            email = f"{username}@example.com"
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password='password123',
                first_name=first_name,
                last_name=last_name,
                phone_number=f"+1{random.randint(1000000000, 9999999999)}"
            )
            users.append(user)
        
        # Create a superuser for testing
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )
        
        return users

    def create_listings(self, users, count):
        """Create sample listings"""
        self.stdout.write(f'Creating {count} listings...')
        
        listings = []
        property_types = ['Apartment', 'House', 'Condo', 'Villa', 'Studio', 'Loft']
        locations = [
            'New York, NY', 'Los Angeles, CA', 'Chicago, IL', 'Miami, FL',
            'San Francisco, CA', 'Seattle, WA', 'Boston, MA', 'Austin, TX',
            'Denver, CO', 'Portland, OR', 'Nashville, TN', 'Atlanta, GA'
        ]
        
        amenities = [
            'WiFi', 'Kitchen', 'Pool', 'Gym', 'Parking', 'Pet-friendly',
            'Air conditioning', 'Heating', 'Washer/Dryer', 'Balcony'
        ]
        
        for i in range(count):
            host = random.choice(users)
            property_type = random.choice(property_types)
            location = random.choice(locations)
            
            name = f"Beautiful {property_type} in {location.split(',')[0]}"
            description = f"A wonderful {property_type.lower()} located in the heart of {location}. " \
                         f"Perfect for travelers looking for comfort and convenience. " \
                         f"Features: {', '.join(random.sample(amenities, random.randint(3, 6)))}"
            
            listing = Listing.objects.create(
                host=host,
                name=name,
                description=description,
                location=location,
                price_per_night=Decimal(str(random.randint(50, 500)))
            )
            listings.append(listing)
        
        return listings

    def create_bookings(self, users, listings, count):
        """Create sample bookings"""
        self.stdout.write(f'Creating {count} bookings...')
        
        bookings = []
        statuses = list(BookingStatus.objects.all())
        
        for i in range(count):
            user = random.choice(users)
            listing = random.choice(listings)
            
            # Ensure user is not the host of the listing
            if user == listing.host:
                continue
            
            # Random dates within the last year or next 6 months
            base_date = datetime.now().date()
            start_offset = random.randint(-365, 180)
            duration = random.randint(1, 14)
            
            start_date = base_date + timedelta(days=start_offset)
            end_date = start_date + timedelta(days=duration)
            
            # Check for overlapping bookings
            overlapping = Booking.objects.filter(
                property=listing,
                start_date__lt=end_date,
                end_date__gt=start_date
            ).exists()
            
            if overlapping:
                continue
            
            total_price = listing.price_per_night * duration
            status = random.choice(statuses)
            
            booking = Booking.objects.create(
                property=listing,
                user=user,
                start_date=start_date,
                end_date=end_date,
                total_price=total_price,
                status=status
            )
            bookings.append(booking)
        
        return bookings

    def create_reviews(self, users, listings, bookings):
        """Create sample reviews"""
        self.stdout.write('Creating reviews...')
        
        # Only create reviews for completed bookings
        completed_bookings = [
            booking for booking in bookings 
            if booking.status.status_name == 'completed'
        ]
        
        review_comments = [
            "Great place to stay! Very clean and comfortable.",
            "Perfect location and amazing host. Highly recommended!",
            "Beautiful property with all the amenities we needed.",
            "Lovely space, exactly as described. Would stay again!",
            "Fantastic experience! The host was very responsive.",
            "Clean, comfortable, and in a great location.",
            "Everything was perfect. Great value for money!",
            "Amazing property! Felt like home away from home.",
            "Excellent stay! The place exceeded our expectations.",
            "Would definitely recommend to friends and family!"
        ]
        
        # Create reviews for some completed bookings
        for booking in random.sample(completed_bookings, min(len(completed_bookings), 30)):
            # Check if review already exists
            if not Review.objects.filter(property=booking.property, user=booking.user).exists():
                Review.objects.create(
                    property=booking.property,
                    user=booking.user,
                    rating=random.randint(3, 5),
                    comment=random.choice(review_comments)
                )

    def create_payments(self, bookings):
        """Create sample payments"""
        self.stdout.write('Creating payments...')
        
        payment_methods = list(PaymentMethod.objects.all())
        
        # Create payments for confirmed and completed bookings
        eligible_bookings = [
            booking for booking in bookings 
            if booking.status.status_name in ['confirmed', 'completed']
        ]
        
        for booking in eligible_bookings:
            Payment.objects.create(
                booking=booking,
                amount=booking.total_price,
                payment_method=random.choice(payment_methods)
            )

    def create_messages(self, users):
        """Create sample messages"""
        self.stdout.write('Creating messages...')
        
        message_templates = [
            "Hi! I'm interested in your property. Is it available for the dates I selected?",
            "Thank you for accepting my booking request!",
            "Could you please provide directions to the property?",
            "Is parking available at your property?",
            "Thank you for the great stay! The place was perfect.",
            "Hi! I have a question about your property amenities.",
            "Are pets allowed in your property?",
            "What's the check-in process?",
            "Thank you for being such a great host!",
            "Is there a grocery store nearby?"
        ]
        
        # Create random messages between users
        for i in range(50):
            sender = random.choice(users)
            recipient = random.choice(users)
            
            # Don't send messages to yourself
            if sender == recipient:
                continue
            
            Message.objects.create(
                sender=sender,
                recipient=recipient,
                message_body=random.choice(message_templates)
            )