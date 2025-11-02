import random
import uuid

from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from listings.models import Listings, Location
from django.contrib.auth import get_user_model


User = get_user_model()

class Command(BaseCommand):
    help = 'seed the database with sample Listings data'

    def add_arguments(self, parser):
        parser.add_argument(
                '--number',
                type=int,
                default=10,
                help='Number of listings to create'
            )
        parser.argument(
                '--delete',
                action='store_true',
                help='Delete existing listings before seeding'
            )

    def handle(self, *args, **options):
        fake = Faker()
        number = options['number']
        do_delete = options['delete']

        #optionally delete existing listings
        if do_delete:
            self.stdout.write(self.style.WARNING('Deleting existing Listing...'))
            Listings.objects.all().delete()

        #Get some host users to assign as host_id
        users = list(User.objects.all())
        if not users:
            self.stdout.write(self.style.ERROR('No users available. Please create some users first.'))
            return

        #Get locations to assign
        locations = list(Location.objects.all())
        if not locations:
            self.stdout.write(self.style.ERROR('No locations available. Please create some locations first.'))
            return
        self.stdout.write(self.style.NOTICE(f'Creating {number} listings...'))

        listings_to_create = []
        for _ in range(number):
            host = random.choice(users)
            location = random.choice(locations)

            name = fake.sentence(nb_words=5).rstrip('.')
            description = fake.paragraph(nb_sentences=3)
            #price per night: random decimal between say $20 and $500
            price = round(random.uniform(20.0, 500.0), 2)

            listing = Listing(
                    # property_id will auto-generate
                    host_id=host,
                    name=name,
                    description=description,
                    location_id=location,
                    price_per_night=price
                )
            listings_to_create.append(listing)

        Listing.objects.bulk_create(listings_to_create)

        self.stdout.write(self.style.SUCCESS(f'Successfully created {len(listing_to_create)} listings'))
            
