from django.core.management.base import BaseCommand
from properties.models import Room


class Command(BaseCommand):
    help = 'Sync all room statuses based on current bookings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--room-code',
            type=str,
            help='Sync only a specific room by code',
        )

    def handle(self, *args, **options):
        room_code = options.get('room_code')

        if room_code:
            rooms = Room.objects.filter(room_code=room_code)
        else:
            rooms = Room.objects.all()

        updated_count = 0
        total_rooms = rooms.count()

        self.stdout.write(f"Syncing room statuses for {total_rooms} rooms...")

        for room in rooms:
            old_status = room.status
            room.update_status_from_bookings()

            if room.status != old_status:
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Updated {room.room_code}: {old_status} → {room.status}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'No change for {room.room_code}: {old_status}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} rooms out of {total_rooms}')
        )