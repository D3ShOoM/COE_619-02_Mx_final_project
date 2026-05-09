import json
from django.conf import settings
from django.db.models import Max
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Bus, FeedEvent, OccupancyReading, PositionPing, Route, Stop
from .services.eta import estimate_stop_etas
from .services.geo import cumulative_distances, project_to_polyline
from .services.occupancy import clamp_count, occupancy_level
from .services.simulation import tick_all_buses


def _auto_tick():
    if getattr(settings, 'SHUTTLE_AUTO_SIMULATE', True):
        try:
            tick_all_buses(max_age_seconds=2)
        except Exception as exc:  # Keep API resilient during first run before seed data exists.
            FeedEvent.objects.create(level=FeedEvent.WARN, component='simulator', message=f'Auto-tick skipped: {exc}')


def _json_error(message, status=400):
    return JsonResponse({'ok': False, 'error': message}, status=status)


def _bus_online(bus):
    age = bus.seconds_since_seen
    if age is None:
        return False
    return age <= getattr(settings, 'SHUTTLE_STALE_SECONDS', 35)


def _iso(dt):
    return dt.isoformat() if dt else None


def rider_map(request):
    return render(request, 'shuttle/map.html', {'page_title': 'Rider Map'})


def dashboard(request):
    return render(request, 'shuttle/dashboard.html', {'page_title': 'Operator Dashboard'})


def about(request):
    return render(request, 'shuttle/about.html', {'page_title': 'About the Demo'})


def api_docs(request):
    return render(request, 'shuttle/api_docs.html', {'page_title': 'API Reference'})


@require_GET
def api_stops(request):
    _auto_tick()
    route = Route.objects.first()
    stops = Stop.objects.filter(is_active=True).select_related('route').order_by('route', 'sequence')
    if route and request.GET.get('route_id'):
        stops = stops.filter(route__route_id=request.GET['route_id'])
    shape = []
    if route:
        shape = [
            {'lat': p.lat, 'lon': p.lon, 'sequence': p.sequence, 'distance_m': round(p.distance_m, 1)}
            for p in route.shape_points.order_by('sequence')
        ]
    return JsonResponse({
        'ok': True,
        'route': None if not route else {
            'route_id': route.route_id,
            'name': route.name,
            'color': route.color,
            'total_length_m': round(route.total_length_m, 1),
        },
        'shape': shape,
        'stops': [
            {
                'stop_id': s.stop_id,
                'name': s.name,
                'sequence': s.sequence,
                'lat': s.lat,
                'lon': s.lon,
                'distance_m': round(s.distance_m, 1),
            }
            for s in stops
        ],
    })


@require_GET
def api_vehicles(request):
    _auto_tick()
    buses = Bus.objects.filter(is_active=True).select_related('route').order_by('bus_id')
    return JsonResponse({
        'ok': True,
        'timestamp': timezone.now().isoformat(),
        'vehicles': [_vehicle_payload(bus) for bus in buses],
    })


def _vehicle_payload(bus):
    age = bus.seconds_since_seen
    return {
        'bus_id': bus.bus_id,
        'label': bus.label,
        'route_id': bus.route.route_id,
        'route_name': bus.route.name,
        'lat': bus.last_lat,
        'lon': bus.last_lon,
        'heading': round(bus.heading or 0, 1),
        'speed_mps': round(bus.speed_mps or 0, 2),
        'speed_kmh': round((bus.speed_mps or 0) * 3.6, 1),
        'progress_m': round(bus.progress_m or 0, 1),
        'current_segment_index': bus.current_segment_index,
        'occupancy_count': bus.current_occupancy,
        'capacity': bus.capacity,
        'occupancy_level': bus.occupancy_level,
        'occupancy_percent': round(100 * bus.current_occupancy / max(1, bus.capacity), 1),
        'last_seen': _iso(bus.last_seen),
        'seconds_since_seen': None if age is None else round(age, 1),
        'online': _bus_online(bus),
    }


@require_GET
def api_history(request, bus_id):
    bus = get_object_or_404(Bus, bus_id=bus_id)
    limit = min(200, max(1, int(request.GET.get('limit', '60'))))
    pings = bus.position_pings.order_by('-created_at')[:limit]
    return JsonResponse({
        'ok': True,
        'bus_id': bus.bus_id,
        'history': [
            {
                'lat': p.lat,
                'lon': p.lon,
                'speed_mps': round(p.speed_mps, 2),
                'heading': round(p.heading, 1),
                'progress_m': round(p.progress_m, 1),
                'segment_index': p.segment_index,
                'source': p.source,
                'created_at': p.created_at.isoformat(),
            }
            for p in reversed(list(pings))
        ],
    })


@require_GET
def api_vehicle_positions(request):
    _auto_tick()
    now = timezone.now()
    entities = []
    for bus in Bus.objects.filter(is_active=True).select_related('route').order_by('bus_id'):
        if bus.last_lat is None or bus.last_lon is None:
            continue
        entities.append({
            'id': bus.bus_id,
            'vehicle': {
                'trip': {'trip_id': f'{bus.route.route_id}-LOOP', 'route_id': bus.route.route_id},
                'vehicle': {'id': bus.bus_id, 'label': bus.label},
                'position': {
                    'latitude': bus.last_lat,
                    'longitude': bus.last_lon,
                    'bearing': round(bus.heading or 0, 1),
                    'speed': round(bus.speed_mps or 0, 2),
                },
                'timestamp': int(bus.last_seen.timestamp()) if bus.last_seen else None,
                'occupancy_status': bus.occupancy_level,
                'current_stop_sequence': bus.current_segment_index + 1,
            },
        })
    latest = PositionPing.objects.aggregate(latest=Max('created_at'))['latest']
    freshness = None if not latest else round((now - latest).total_seconds(), 1)
    return JsonResponse({
        'header': {
            'gtfs_realtime_version': '2.0-json-demo',
            'timestamp': int(now.timestamp()),
            'feed_freshness_seconds': freshness,
        },
        'entity': entities,
    })


@require_GET
def api_trip_updates(request):
    _auto_tick()
    now = timezone.now()
    entities = []
    for bus in Bus.objects.filter(is_active=True).select_related('route').prefetch_related('route__stops', 'route__segment_stats'):
        etas = estimate_stop_etas(bus)
        entities.append({
            'id': f'{bus.bus_id}-trip-update',
            'trip_update': {
                'trip': {'trip_id': f'{bus.route.route_id}-LOOP', 'route_id': bus.route.route_id},
                'vehicle': {'id': bus.bus_id, 'label': bus.label},
                'timestamp': int(now.timestamp()),
                'occupancy_status': bus.occupancy_level,
                'stop_time_update': [
                    {
                        'stop_id': eta['stop_id'],
                        'stop_name': eta['stop_name'],
                        'stop_sequence': eta['sequence'],
                        'arrival': {
                            'time': eta['arrival_epoch'],
                            'iso': eta['arrival_time'],
                            'delay': 0,
                        },
                        'eta_seconds': eta['eta_seconds'],
                        'eta_minutes': eta['eta_minutes'],
                        'distance_m': eta['distance_m'],
                    }
                    for eta in etas
                ],
            },
        })
    return JsonResponse({
        'header': {'gtfs_realtime_version': '2.0-json-demo', 'timestamp': int(now.timestamp())},
        'entity': entities,
    })


@require_GET
def api_feed_health(request):
    _auto_tick()
    now = timezone.now()
    buses = list(Bus.objects.filter(is_active=True))
    online = [b for b in buses if _bus_online(b)]
    latest = PositionPing.objects.aggregate(latest=Max('created_at'))['latest']
    freshness = None if not latest else round((now - latest).total_seconds(), 1)
    return JsonResponse({
        'ok': True,
        'timestamp': now.isoformat(),
        'auto_simulate': getattr(settings, 'SHUTTLE_AUTO_SIMULATE', True),
        'vehicle_count': len(buses),
        'online_vehicle_count': len(online),
        'stale_vehicle_count': len(buses) - len(online),
        'feed_freshness_seconds': freshness,
        'target_update_cadence_seconds': getattr(settings, 'SHUTTLE_UPDATE_CADENCE_SECONDS', 20),
        'position_ping_count': PositionPing.objects.count(),
        'occupancy_reading_count': OccupancyReading.objects.count(),
        'status': 'OK' if len(online) == len(buses) and buses else 'WARN',
    })


@require_GET
def api_logs(request):
    limit = min(100, max(1, int(request.GET.get('limit', '20'))))
    events = FeedEvent.objects.order_by('-created_at')[:limit]
    return JsonResponse({
        'ok': True,
        'events': [
            {
                'level': e.level,
                'component': e.component,
                'message': e.message,
                'created_at': e.created_at.isoformat(),
            }
            for e in events
        ],
    })


@csrf_exempt
@require_POST
def api_ingest_gps(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return _json_error('Invalid JSON body.')

    bus_id = data.get('bus_id')
    if not bus_id:
        return _json_error('bus_id is required.')
    try:
        lat = float(data['lat'])
        lon = float(data['lon'])
    except (KeyError, TypeError, ValueError):
        return _json_error('lat and lon are required numeric fields.')

    bus = get_object_or_404(Bus, bus_id=bus_id)
    route = bus.route
    shape = list(route.shape_points.order_by('sequence'))
    points = [(p.lat, p.lon) for p in shape]
    distances = [p.distance_m for p in shape]
    if len(points) >= 2:
        snap = project_to_polyline(lat, lon, points, distances)
        progress = snap['progress_m']
        segment_index = snap['segment_index']
        route_error_m = snap['distance_to_route_m']
        if route_error_m < 80:
            # Snap noisy campus GPS points back to the route for ETA stability.
            lat, lon = snap['lat'], snap['lon']
    else:
        progress = bus.progress_m
        segment_index = bus.current_segment_index
        route_error_m = None

    speed = float(data.get('speed_mps', bus.speed_mps or 0))
    heading = float(data.get('heading', bus.heading or 0))
    source = data.get('source', 'device')
    now = timezone.now()

    bus.last_lat = lat
    bus.last_lon = lon
    bus.speed_mps = speed
    bus.heading = heading
    bus.progress_m = progress
    bus.current_segment_index = segment_index
    bus.last_seen = now
    bus.save(update_fields=['last_lat', 'last_lon', 'speed_mps', 'heading', 'progress_m', 'current_segment_index', 'last_seen'])

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
    if route_error_m is not None and route_error_m > 80:
        FeedEvent.objects.create(level=FeedEvent.WARN, component='gps-ingest', message=f'{bus.bus_id} off-route by {route_error_m:.1f} m')
    return JsonResponse({'ok': True, 'vehicle': _vehicle_payload(bus), 'route_error_m': route_error_m})


@csrf_exempt
@require_POST
def api_ingest_occupancy(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return _json_error('Invalid JSON body.')

    bus_id = data.get('bus_id')
    if not bus_id:
        return _json_error('bus_id is required.')
    bus = get_object_or_404(Bus, bus_id=bus_id)
    if 'count' in data:
        count = clamp_count(data.get('count'), bus.capacity)
    else:
        delta = int(data.get('boardings', 0)) - int(data.get('alightings', 0))
        count = clamp_count(bus.current_occupancy + delta, bus.capacity)

    level = occupancy_level(count, bus.capacity, bus.occupancy_level)
    boardings = max(0, int(data.get('boardings', 0)))
    alightings = max(0, int(data.get('alightings', 0)))
    source = data.get('source', 'device')
    bus.current_occupancy = count
    bus.occupancy_level = level
    bus.save(update_fields=['current_occupancy', 'occupancy_level'])
    reading = OccupancyReading.objects.create(
        bus=bus,
        count=count,
        level=level,
        boardings=boardings,
        alightings=alightings,
        source=source,
    )
    return JsonResponse({
        'ok': True,
        'bus_id': bus.bus_id,
        'count': count,
        'level': level,
        'created_at': reading.created_at.isoformat(),
    })
