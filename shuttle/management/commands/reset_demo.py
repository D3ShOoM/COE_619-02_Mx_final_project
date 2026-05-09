from django.core.management.base import BaseCommand, CommandError
from shuttle.models import Bus, FeedEvent, OccupancyReading, PositionPing, Route, RouteShapePoint, SegmentStat, Stop


class Command(BaseCommand):
    help = 'Delete all demo data.'

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='Confirm deletion without prompt.')

    def handle(self, *args, **options):
        if not options['yes']:
            raise CommandError('This deletes demo data. Re-run with --yes to confirm.')
        for model in [PositionPing, OccupancyReading, SegmentStat, Bus, RouteShapePoint, Stop, Route, FeedEvent]:
            model.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Demo data deleted.'))
