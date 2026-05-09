from django.contrib import admin
from .models import Bus, FeedEvent, OccupancyReading, PositionPing, Route, RouteShapePoint, SegmentStat, Stop


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('route_id', 'name', 'total_length_m', 'color')
    search_fields = ('route_id', 'name')


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ('sequence', 'stop_id', 'name', 'route', 'distance_m', 'is_active')
    list_filter = ('route', 'is_active')
    search_fields = ('stop_id', 'name')


@admin.register(RouteShapePoint)
class RouteShapePointAdmin(admin.ModelAdmin):
    list_display = ('route', 'sequence', 'lat', 'lon', 'distance_m')
    list_filter = ('route',)


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('bus_id', 'label', 'route', 'current_occupancy', 'occupancy_level', 'speed_mps', 'last_seen', 'is_active')
    list_filter = ('route', 'occupancy_level', 'is_active')
    search_fields = ('bus_id', 'label')


@admin.register(PositionPing)
class PositionPingAdmin(admin.ModelAdmin):
    list_display = ('bus', 'lat', 'lon', 'speed_mps', 'progress_m', 'segment_index', 'source', 'created_at')
    list_filter = ('source', 'bus')
    date_hierarchy = 'created_at'


@admin.register(OccupancyReading)
class OccupancyReadingAdmin(admin.ModelAdmin):
    list_display = ('bus', 'count', 'level', 'boardings', 'alightings', 'source', 'created_at')
    list_filter = ('level', 'source', 'bus')
    date_hierarchy = 'created_at'


@admin.register(SegmentStat)
class SegmentStatAdmin(admin.ModelAdmin):
    list_display = ('segment_index', 'route', 'from_stop', 'to_stop', 'distance_m', 'observed_travel_time_s', 'variance', 'updated_at')
    list_filter = ('route',)


@admin.register(FeedEvent)
class FeedEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'level', 'component', 'message')
    list_filter = ('level', 'component')
    search_fields = ('message', 'component')
    date_hierarchy = 'created_at'
