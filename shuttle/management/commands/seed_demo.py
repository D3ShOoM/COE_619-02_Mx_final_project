from django.core.management.base import BaseCommand
from django.utils import timezone
from shuttle.models import Bus, FeedEvent, OccupancyReading, PositionPing, Route, RouteShapePoint, SegmentStat, Stop
from shuttle.services.geo import bearing_degrees, cumulative_distances, interpolate_along_points, path_length_m
from shuttle.services.eta import segment_distance_between_stops
from shuttle.services.occupancy import occupancy_level


STOP_DATA = [
    ('KFUPM-S1', 'Main Gate / Arrival', 26.306350, 50.147000),
    ('KFUPM-S2', 'Library / Academic Core', 26.307900, 50.151200),
    ('KFUPM-S3', 'Student Center', 26.311200, 50.150100),
    ('KFUPM-S4', 'Dorms / Housing', 26.312300, 50.144800),
]

# Additional points make the loop look more natural than straight stop-to-stop lines.
SHAPE_POINTS = [
    (26.306350, 50.147000),
    (26.306950, 50.149400),
    (26.307900, 50.151200),
    (26.309600, 50.151500),
    (26.311200, 50.150100),
    (26.312500, 50.147800),
    (26.312300, 50.144800),
    (26.309900, 50.144200),
    (26.306350, 50.147000),
]


class Command(BaseCommand):
    help = 'Seed a runnable 4-stop, 2-bus campus shuttle demo.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete old demo data before seeding.')

    def handle(self, *args, **options):
        if options['reset']:
            for model in [PositionPing, OccupancyReading, SegmentStat, Bus, RouteShapePoint, Stop, Route, FeedEvent]:
                model.objects.all().delete()

        route, _ = Route.objects.update_or_create(
            route_id='KFUPM-LOOP',
            defaults={'name': 'KFUPM 4-Stop Pilot Loop', 'color': '#00843D'},
        )

        distances = cumulative_distances(SHAPE_POINTS)
        total = distances[-1]
        route.total_length_m = total
        route.save(update_fields=['total_length_m'])

        RouteShapePoint.objects.filter(route=route).delete()
        for seq, ((lat, lon), dist) in enumerate(zip(SHAPE_POINTS, distances), start=1):
            RouteShapePoint.objects.create(route=route, sequence=seq, lat=lat, lon=lon, distance_m=dist)

        Stop.objects.filter(route=route).delete()
        stop_objects = []
        for seq, (stop_id, name, lat, lon) in enumerate(STOP_DATA, start=1):
            # Use the closest shape distance for the stop.
            best_dist = min(distances, key=lambda d: abs(interpolate_along_points(SHAPE_POINTS, distances, d)[0] - lat) + abs(interpolate_along_points(SHAPE_POINTS, distances, d)[1] - lon))
            stop = Stop.objects.create(
                stop_id=stop_id,
                route=route,
                name=name,
                sequence=seq,
                lat=lat,
                lon=lon,
                distance_m=best_dist,
            )
            stop_objects.append(stop)

        SegmentStat.objects.filter(route=route).delete()
        for idx, stop in enumerate(stop_objects):
            next_stop = stop_objects[(idx + 1) % len(stop_objects)]
            segment_distance = segment_distance_between_stops(stop, next_stop, total)
            # Conservative campus loop speed plus a small dwell allowance.
            travel_time = max(35.0, segment_distance / 5.0 + 10.0)
            SegmentStat.objects.create(
                route=route,
                from_stop=stop,
                to_stop=next_stop,
                segment_index=idx,
                distance_m=segment_distance,
                observed_travel_time_s=travel_time,
                variance=420.0,
            )

        now = timezone.now()
        Bus.objects.filter(route=route).delete()
        bus_specs = [
            ('BUS-01', 'Campus Shuttle 01', 40, 0.0, 4.8, 0.0),
            ('BUS-02', 'Campus Shuttle 02', 36, total * 0.52, 4.4, 2.7),
        ]
        for bus_id, label, capacity, progress, speed, phase in bus_specs:
            lat, lon, heading = interpolate_along_points(SHAPE_POINTS, distances, progress)
            count = int(capacity * (0.32 if bus_id.endswith('01') else 0.58))
            level = occupancy_level(count, capacity)
            bus = Bus.objects.create(
                bus_id=bus_id,
                label=label,
                route=route,
                capacity=capacity,
                current_occupancy=count,
                occupancy_level=level,
                last_lat=lat,
                last_lon=lon,
                heading=heading,
                speed_mps=speed,
                progress_m=progress,
                current_segment_index=0,
                last_seen=now,
                demo_speed_mps=speed,
                demo_phase=phase,
            )
            PositionPing.objects.create(
                bus=bus,
                lat=lat,
                lon=lon,
                speed_mps=speed,
                heading=heading,
                progress_m=progress,
                segment_index=0,
                source='seed-demo',
            )
            OccupancyReading.objects.create(bus=bus, count=count, level=level, source='seed-demo')

        FeedEvent.objects.create(level=FeedEvent.INFO, component='seed', message='Seeded KFUPM 4-stop demo loop with two buses.')
        self.stdout.write(self.style.SUCCESS('Seeded demo route KFUPM-LOOP with 4 stops and 2 buses.'))
        self.stdout.write(f'Route length: {total:.1f} m')
