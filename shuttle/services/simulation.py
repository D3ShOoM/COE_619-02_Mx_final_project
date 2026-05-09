import math
import random
from django.utils import timezone
from .geo import bearing_degrees, cumulative_distances, interpolate_along_points
from .occupancy import clamp_count, occupancy_level
from shuttle.models import FeedEvent, OccupancyReading, PositionPing, Route, Bus


def _route_points(route):
    shape = list(route.shape_points.order_by('sequence'))
    if shape:
        points = [(p.lat, p.lon) for p in shape]
        distances = [p.distance_m for p in shape]
        if distances and distances[-1] > 0:
            return points, distances
    stops = list(route.stops.order_by('sequence'))
    points = [(s.lat, s.lon) for s in stops]
    if points and points[0] != points[-1]:
        points.append(points[0])
    return points, cumulative_distances(points)


def _segment_index_for_progress(route, progress_m):
    stops = list(route.stops.order_by('sequence'))
    if not stops:
        return 0
    total = max(1.0, route.total_length_m)
    p = progress_m % total
    for idx, stop in enumerate(stops):
        start = stop.distance_m
        end = stops[(idx + 1) % len(stops)].distance_m
        if end <= start:
            end += total
        pn = p if p >= start else p + total
        if start <= pn <= end:
            return idx
    return 0


def advance_bus(bus, seconds=None, source='auto-simulator', jitter=False):
    route = bus.route
    points, distances = _route_points(route)
    if len(points) < 2:
        return bus
    total = max(route.total_length_m or distances[-1], 1.0)
    now = timezone.now()
    if seconds is None:
        if bus.last_seen:
            seconds = max(0.0, (now - bus.last_seen).total_seconds())
        else:
            seconds = 2.0
    seconds = min(max(seconds, 0.0), 30.0)

    wave = 1.0 + 0.18 * math.sin((now.timestamp() / 28.0) + bus.demo_phase)
    speed = max(1.5, bus.demo_speed_mps * wave)
    progress = (bus.progress_m + speed * seconds) % total
    lat, lon, heading = interpolate_along_points(points, distances, progress)
    if jitter:
        lat += random.uniform(-0.000015, 0.000015)
        lon += random.uniform(-0.000015, 0.000015)
    segment_index = _segment_index_for_progress(route, progress)

    bus.progress_m = progress
    bus.last_lat = lat
    bus.last_lon = lon
    bus.heading = heading
    bus.speed_mps = speed
    bus.current_segment_index = segment_index
    bus.last_seen = now

    # Small deterministic occupancy variation for a realistic board.
    capacity = bus.capacity
    base = 0.42 + 0.24 * math.sin((progress / total) * math.tau + bus.demo_phase)
    noisy = int(round(capacity * max(0.08, min(0.92, base))))
    count = clamp_count(noisy, capacity)
    level = occupancy_level(count, capacity, bus.occupancy_level)
    occupancy_changed = count != bus.current_occupancy or level != bus.occupancy_level
    bus.current_occupancy = count
    bus.occupancy_level = level
    bus.save(update_fields=[
        'progress_m', 'last_lat', 'last_lon', 'heading', 'speed_mps',
        'current_segment_index', 'last_seen', 'current_occupancy', 'occupancy_level'
    ])

    PositionPing.objects.create(
        bus=bus,
        lat=lat,
        lon=lon,
        speed_mps=speed,
        heading=heading,
        progress_m=progress,
        segment_index=segment_index,
        source=source,
    )
    if occupancy_changed:
        OccupancyReading.objects.create(
            bus=bus,
            count=count,
            level=level,
            source=source,
        )
    return bus


def tick_all_buses(max_age_seconds=2, source='auto-simulator'):
    now = timezone.now()
    updated = []
    for bus in Bus.objects.filter(is_active=True).select_related('route'):
        if bus.last_seen is None:
            seconds = 2
        else:
            seconds = (now - bus.last_seen).total_seconds()
        if seconds >= max_age_seconds:
            updated.append(advance_bus(bus, seconds=seconds, source=source))
    if updated:
        FeedEvent.objects.create(
            level=FeedEvent.INFO,
            component='simulator',
            message=f'Advanced {len(updated)} bus(es) for demo feed freshness.',
        )
    return updated
