from datetime import timedelta
from django.utils import timezone
from .geo import haversine_m


class KalmanTravelTime:
    """Small scalar Kalman update for segment travel-time smoothing."""

    def __init__(self, process_var=30.0, measurement_var=90.0):
        self.process_var = process_var
        self.measurement_var = measurement_var

    def update(self, mean_s, variance, observed_s):
        predicted_variance = float(variance) + self.process_var
        gain = predicted_variance / (predicted_variance + self.measurement_var)
        updated_mean = float(mean_s) + gain * (float(observed_s) - float(mean_s))
        updated_variance = (1 - gain) * predicted_variance
        return max(5.0, updated_mean), max(1.0, updated_variance)


def _stop_boundaries(stops, total_length_m):
    ordered = list(stops)
    if not ordered:
        return []
    return [(stop.sequence - 1, stop, stop.distance_m % max(total_length_m, 1)) for stop in ordered]


def _distance_forward(current_m, target_m, total_length_m):
    total = max(1.0, total_length_m)
    return (target_m - current_m) % total


def _segments_between(current_m, target_m, stops, stats_by_index, total_length_m):
    """Approximate travel time from current progress to a target stop.

    The demo route has one segment between each stop, including the loop from the
    last stop back to the first. This function estimates partial and full segment
    travel times using the current speed and the learned segment profile.
    """
    if not stops:
        return 0.0, 0

    ordered = list(stops)
    boundaries = [stop.distance_m for stop in ordered]
    total = max(1.0, total_length_m)
    target = target_m % total
    current = current_m % total
    forward = _distance_forward(current, target, total)
    if forward < 2:
        return 0.0, 0

    remaining = forward
    cursor = current
    estimated = 0.0
    stops_crossed = 0

    for _ in range(len(ordered) + 2):
        # Find the next stop boundary ahead of cursor.
        ahead = [d for d in boundaries if d > cursor + 0.5]
        next_boundary = min(ahead) if ahead else boundaries[0] + total
        travel_piece = min(remaining, next_boundary - cursor)

        segment_index = 0
        for idx, stop in enumerate(ordered):
            start = stop.distance_m
            end = ordered[(idx + 1) % len(ordered)].distance_m
            if end <= start:
                end += total
            cursor_norm = cursor if cursor >= start else cursor + total
            if start <= cursor_norm <= end:
                segment_index = idx
                break

        stat = stats_by_index.get(segment_index)
        if stat and stat.distance_m > 0:
            profile_speed = max(1.0, stat.distance_m / max(5.0, stat.observed_travel_time_s))
        else:
            profile_speed = 5.0
        estimated += travel_piece / profile_speed
        remaining -= travel_piece
        cursor = (cursor + travel_piece) % total
        if remaining <= 0.5:
            break
        stops_crossed += 1
        estimated += 12.0  # short dwell allowance at intermediate stops

    return estimated, stops_crossed


def estimate_stop_etas(bus):
    route = bus.route
    stops = list(route.stops.filter(is_active=True).order_by('sequence'))
    stats_by_index = {s.segment_index: s for s in route.segment_stats.all()}
    total = max(route.total_length_m, 1.0)
    current = bus.progress_m % total
    now = timezone.now()
    results = []

    for stop in stops:
        base_s, stops_crossed = _segments_between(current, stop.distance_m, stops, stats_by_index, total)
        # Blend current speed into the profile estimate for short horizons.
        forward_m = _distance_forward(current, stop.distance_m, total)
        if bus.speed_mps and bus.speed_mps > 0.5:
            current_speed_s = forward_m / max(1.0, bus.speed_mps)
            weight = 0.65 if forward_m < 600 else 0.35
            eta_s = weight * current_speed_s + (1 - weight) * base_s
        else:
            eta_s = base_s
        eta_s = max(0.0, eta_s)
        arrival = now + timedelta(seconds=eta_s)
        results.append({
            'stop_id': stop.stop_id,
            'stop_name': stop.name,
            'sequence': stop.sequence,
            'distance_m': round(forward_m, 1),
            'eta_seconds': int(round(eta_s)),
            'eta_minutes': round(eta_s / 60.0, 1),
            'arrival_time': arrival.isoformat(),
            'arrival_epoch': int(arrival.timestamp()),
            'intermediate_stops': stops_crossed,
        })
    results.sort(key=lambda row: row['eta_seconds'])
    return results


def update_segment_stat(stat, observed_travel_time_s):
    smoother = KalmanTravelTime()
    mean, variance = smoother.update(stat.observed_travel_time_s, stat.variance, observed_travel_time_s)
    stat.observed_travel_time_s = mean
    stat.variance = variance
    stat.save(update_fields=['observed_travel_time_s', 'variance', 'updated_at'])
    return stat


def segment_distance_between_stops(a, b, total_length_m):
    direct = b.distance_m - a.distance_m
    if direct <= 0:
        direct += total_length_m
    return direct if direct > 0 else haversine_m(a.lat, a.lon, b.lat, b.lon)
