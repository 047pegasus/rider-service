"""
Management command to create test riders with initial locations.
Usage: python manage.py create_test_riders
"""
from django.core.management.base import BaseCommand
from apps.riders.models import Rider, RiderLocation
from apps.riders.services import rider_service


class Command(BaseCommand):
    help = 'Create test riders with initial locations for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=6,
            help='Number of test riders to create (default: 5)',
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # Default locations in Delhi area (can be modified)
        default_locations = [
            {"lat": 28.6139, "lng": 77.2090, "name": "Rider 1"},  # Delhi center
            {"lat": 28.5355, "lng": 77.3910, "name": "Rider 2"},  # Gurgaon
            {"lat": 28.4089, "lng": 77.0378, "name": "Rider 3"},  # Noida
            {"lat": 28.7041, "lng": 77.1025, "name": "Rider 4"},  # North Delhi
            {"lat": 28.4595, "lng": 77.0266, "name": "Rider 5"},  # South Delhi
            {"lat": 26.9427, "lng": 80.9392, "name": "Rider 6"},  # Lucknow
        ]
        
        created_count = 0
        
        for i in range(count):
            location_data = default_locations[i % len(default_locations)]
            
            # Create rider
            rider, created = Rider.objects.get_or_create(
                phone=f"9876543{i:03d}",
                defaults={
                    'name': f"{location_data['name']}",
                    'email': f"rider{i+1}@test.com",
                    'vehicle_type': ['bike', 'car', 'scooter'][i % 3],
                    'is_active': True,
                    'current_status': 'available',
                }
            )
            
            if created:
                # Set initial location
                rider_service.update_rider_location(
                    rider_id=str(rider.id),
                    location_data={
                        'lat': location_data['lat'],
                        'lng': location_data['lng'],
                        'accuracy': 10.0,
                        'speed': 0.0,
                    }
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created rider: {rider.name} (Phone: {rider.phone}) at '
                        f'({location_data["lat"]}, {location_data["lng"]})'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Rider with phone {rider.phone} already exists, skipping...'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created {created_count} test riders with locations!'
            )
        )
