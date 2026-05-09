import time
from django.core.management.base import BaseCommand
from shuttle.services.simulation import advance_bus
from shuttle.models import Bus, FeedEvent


class Command(BaseCommand):
    help = 'Continuously simulate demo buses. Run in a second terminal during demos.'

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=float, default=2.0, help='Seconds between simulator ticks.')
        parser.add_argument('--jitter', action='store_true', help='Add small GPS jitter to demonstrate route snapping/robustness.')
        parser.add_argument('--once', action='store_true', help='Advance once and exit.')

    def handle(self, *args, **options):
        interval = max(0.5, float(options['interval']))
        self.stdout.write(self.style.SUCCESS(f'Starting simulator with interval={interval}s. Press Ctrl+C to stop.'))
        try:
            while True:
                buses = list(Bus.objects.filter(is_active=True).select_related('route'))
                if not buses:
                    self.stdout.write(self.style.WARNING('No active buses found. Run: python manage.py seed_demo'))
                    return
                for bus in buses:
                    advance_bus(bus, seconds=interval, source='management-simulator', jitter=options['jitter'])
                self.stdout.write(f'Advanced {len(buses)} bus(es).')
                if options['once']:
                    break
                time.sleep(interval)
        except KeyboardInterrupt:
            FeedEvent.objects.create(level=FeedEvent.INFO, component='simulator', message='Simulator stopped by operator.')
            self.stdout.write(self.style.WARNING('Simulator stopped.'))
