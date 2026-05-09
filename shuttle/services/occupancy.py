LOW = 'LOW'
MEDIUM = 'MEDIUM'
HIGH = 'HIGH'


def occupancy_level(count, capacity, previous=None):
    """Return Low/Medium/High with small hysteresis to reduce flicker.

    Baseline thresholds match the proposal: Low < 40%, Medium 40-80%, High > 80%.
    Hysteresis creates a small deadband near the boundaries.
    """
    capacity = max(1, int(capacity or 1))
    ratio = max(0.0, min(1.5, float(count) / capacity))

    low_to_medium = 0.40
    medium_to_high = 0.80
    low_back = 0.35
    high_back = 0.75

    if previous == LOW:
        if ratio >= medium_to_high:
            return HIGH
        if ratio >= low_to_medium:
            return MEDIUM
        return LOW

    if previous == HIGH:
        if ratio <= low_back:
            return LOW
        if ratio <= high_back:
            return MEDIUM
        return HIGH

    if ratio < low_back:
        return LOW
    if ratio > medium_to_high:
        return HIGH
    return MEDIUM


def clamp_count(count, capacity):
    return max(0, min(int(capacity or 0), int(count or 0)))
