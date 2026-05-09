from django.db import models
from django.utils import timezone


class Route(models.Model):
    route_id = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=120)
    color = models.CharField(max_length=12, default='#00843D')
    total_length_m = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['route_id']

    def __str__(self):
        return f'{self.route_id} - {self.name}'


class Stop(models.Model):
    stop_id = models.CharField(max_length=32, unique=True)
    route = models.ForeignKey(Route, related_name='stops', on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    sequence = models.PositiveIntegerField()
    lat = models.FloatField()
    lon = models.FloatField()
    distance_m = models.FloatField(default=0, help_text='Distance along loop from route origin.')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['route', 'sequence']
        unique_together = [('route', 'sequence')]

    def __str__(self):
        return f'{self.sequence}. {self.name}'


class RouteShapePoint(models.Model):
    route = models.ForeignKey(Route, related_name='shape_points', on_delete=models.CASCADE)
    sequence = models.PositiveIntegerField()
    lat = models.FloatField()
    lon = models.FloatField()
    distance_m = models.FloatField(default=0)

    class Meta:
        ordering = ['route', 'sequence']
        unique_together = [('route', 'sequence')]

    def __str__(self):
        return f'{self.route.route_id} shape {self.sequence}'


class Bus(models.Model):
    OCCUPANCY_LOW = 'LOW'
    OCCUPANCY_MEDIUM = 'MEDIUM'
    OCCUPANCY_HIGH = 'HIGH'
    OCCUPANCY_CHOICES = [
        (OCCUPANCY_LOW, 'Low'),
        (OCCUPANCY_MEDIUM, 'Medium'),
        (OCCUPANCY_HIGH, 'High'),
    ]

    bus_id = models.CharField(max_length=32, unique=True)
    label = models.CharField(max_length=120)
    route = models.ForeignKey(Route, related_name='buses', on_delete=models.CASCADE)
    capacity = models.PositiveIntegerField(default=40)
    current_occupancy = models.PositiveIntegerField(default=0)
    occupancy_level = models.CharField(max_length=12, choices=OCCUPANCY_CHOICES, default=OCCUPANCY_LOW)
    last_lat = models.FloatField(null=True, blank=True)
    last_lon = models.FloatField(null=True, blank=True)
    heading = models.FloatField(default=0)
    speed_mps = models.FloatField(default=0)
    progress_m = models.FloatField(default=0, help_text='Distance along loop from route origin.')
    current_segment_index = models.PositiveIntegerField(default=0)
    last_seen = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    demo_speed_mps = models.FloatField(default=4.8)
    demo_phase = models.FloatField(default=0, help_text='Offset used by the simulator to make buses distinct.')

    class Meta:
        ordering = ['bus_id']

    def __str__(self):
        return f'{self.bus_id} ({self.label})'

    @property
    def seconds_since_seen(self):
        if not self.last_seen:
            return None
        return max(0, (timezone.now() - self.last_seen).total_seconds())


class PositionPing(models.Model):
    bus = models.ForeignKey(Bus, related_name='position_pings', on_delete=models.CASCADE)
    lat = models.FloatField()
    lon = models.FloatField()
    speed_mps = models.FloatField(default=0)
    heading = models.FloatField(default=0)
    progress_m = models.FloatField(default=0)
    segment_index = models.PositiveIntegerField(default=0)
    source = models.CharField(max_length=64, default='simulator')
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['bus', '-created_at'])]

    def __str__(self):
        return f'{self.bus.bus_id} ping {self.created_at:%H:%M:%S}'


class OccupancyReading(models.Model):
    bus = models.ForeignKey(Bus, related_name='occupancy_readings', on_delete=models.CASCADE)
    count = models.PositiveIntegerField()
    level = models.CharField(max_length=12, choices=Bus.OCCUPANCY_CHOICES)
    boardings = models.PositiveIntegerField(default=0)
    alightings = models.PositiveIntegerField(default=0)
    source = models.CharField(max_length=64, default='simulator')
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['bus', '-created_at'])]

    def __str__(self):
        return f'{self.bus.bus_id} occupancy {self.count} ({self.level})'


class SegmentStat(models.Model):
    route = models.ForeignKey(Route, related_name='segment_stats', on_delete=models.CASCADE)
    from_stop = models.ForeignKey(Stop, related_name='segments_from', on_delete=models.CASCADE)
    to_stop = models.ForeignKey(Stop, related_name='segments_to', on_delete=models.CASCADE)
    segment_index = models.PositiveIntegerField()
    distance_m = models.FloatField(default=0)
    observed_travel_time_s = models.FloatField(default=90)
    variance = models.FloatField(default=400)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['route', 'segment_index']
        unique_together = [('route', 'segment_index')]

    def __str__(self):
        return f'{self.from_stop.name} -> {self.to_stop.name}'


class FeedEvent(models.Model):
    INFO = 'INFO'
    WARN = 'WARN'
    ERROR = 'ERROR'
    LEVEL_CHOICES = [(INFO, 'Info'), (WARN, 'Warning'), (ERROR, 'Error')]

    level = models.CharField(max_length=8, choices=LEVEL_CHOICES, default=INFO)
    component = models.CharField(max_length=64, default='system')
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.level}] {self.component}: {self.message[:60]}'
