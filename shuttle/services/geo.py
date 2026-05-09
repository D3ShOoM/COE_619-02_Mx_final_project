import math

EARTH_RADIUS_M = 6371000.0


def haversine_m(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing_degrees(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    y = math.sin(dlambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def path_length_m(points):
    if len(points) < 2:
        return 0.0
    total = 0.0
    for a, b in zip(points, points[1:]):
        total += haversine_m(a[0], a[1], b[0], b[1])
    return total


def cumulative_distances(points):
    distances = [0.0]
    total = 0.0
    for a, b in zip(points, points[1:]):
        total += haversine_m(a[0], a[1], b[0], b[1])
        distances.append(total)
    return distances


def interpolate_along_points(points, distances, target_m):
    if not points:
        return None
    if len(points) == 1:
        return points[0][0], points[0][1], 0.0
    total = distances[-1]
    if total <= 0:
        return points[0][0], points[0][1], 0.0
    target = target_m % total
    for idx in range(len(points) - 1):
        start_d = distances[idx]
        end_d = distances[idx + 1]
        if start_d <= target <= end_d:
            span = max(0.001, end_d - start_d)
            ratio = (target - start_d) / span
            lat = points[idx][0] + ratio * (points[idx + 1][0] - points[idx][0])
            lon = points[idx][1] + ratio * (points[idx + 1][1] - points[idx][1])
            heading = bearing_degrees(points[idx][0], points[idx][1], points[idx + 1][0], points[idx + 1][1])
            return lat, lon, heading
    heading = bearing_degrees(points[-2][0], points[-2][1], points[-1][0], points[-1][1])
    return points[-1][0], points[-1][1], heading


def _to_xy_m(lat, lon, ref_lat, ref_lon):
    x = math.radians(lon - ref_lon) * EARTH_RADIUS_M * math.cos(math.radians(ref_lat))
    y = math.radians(lat - ref_lat) * EARTH_RADIUS_M
    return x, y


def _to_latlon(x, y, ref_lat, ref_lon):
    lat = ref_lat + math.degrees(y / EARTH_RADIUS_M)
    lon = ref_lon + math.degrees(x / (EARTH_RADIUS_M * math.cos(math.radians(ref_lat))))
    return lat, lon


def project_to_polyline(lat, lon, points, distances):
    """Project a point onto a small-area polyline.

    Returns a dictionary containing snapped lat/lon, progress along the route,
    segment index, and distance from the route. This is intentionally lightweight
    for a campus loop and avoids GIS dependencies.
    """
    if len(points) < 2:
        return {
            'lat': lat,
            'lon': lon,
            'progress_m': 0.0,
            'segment_index': 0,
            'distance_to_route_m': 0.0,
        }

    ref_lat, ref_lon = lat, lon
    px, py = _to_xy_m(lat, lon, ref_lat, ref_lon)
    best = None
    for idx in range(len(points) - 1):
        ax, ay = _to_xy_m(points[idx][0], points[idx][1], ref_lat, ref_lon)
        bx, by = _to_xy_m(points[idx + 1][0], points[idx + 1][1], ref_lat, ref_lon)
        vx, vy = bx - ax, by - ay
        wx, wy = px - ax, py - ay
        denom = vx * vx + vy * vy
        ratio = 0.0 if denom == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / denom))
        sx, sy = ax + ratio * vx, ay + ratio * vy
        dist = math.hypot(px - sx, py - sy)
        segment_length = max(0.001, distances[idx + 1] - distances[idx])
        progress = distances[idx] + ratio * segment_length
        snapped_lat, snapped_lon = _to_latlon(sx, sy, ref_lat, ref_lon)
        if best is None or dist < best['distance_to_route_m']:
            best = {
                'lat': snapped_lat,
                'lon': snapped_lon,
                'progress_m': progress,
                'segment_index': idx,
                'distance_to_route_m': dist,
            }
    return best


def nearest_stop(lat, lon, stops):
    best = None
    for stop in stops:
        dist = haversine_m(lat, lon, stop.lat, stop.lon)
        if best is None or dist < best[0]:
            best = (dist, stop)
    return best
