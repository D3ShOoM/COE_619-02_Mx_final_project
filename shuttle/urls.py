from django.urls import path
from . import views

urlpatterns = [
    path('', views.rider_map, name='rider_map'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('about/', views.about, name='about'),
    path('api-docs/', views.api_docs, name='api_docs'),

    path('api/stops/', views.api_stops, name='api_stops'),
    path('api/vehicles/', views.api_vehicles, name='api_vehicles'),
    path('api/history/<str:bus_id>/', views.api_history, name='api_history'),
    path('api/feed-health/', views.api_feed_health, name='api_feed_health'),
    path('api/logs/', views.api_logs, name='api_logs'),
    path('api/gtfs-rt/vehicle-positions/', views.api_vehicle_positions, name='api_vehicle_positions'),
    path('api/gtfs-rt/trip-updates/', views.api_trip_updates, name='api_trip_updates'),
    path('api/ingest/gps/', views.api_ingest_gps, name='api_ingest_gps'),
    path('api/ingest/occupancy/', views.api_ingest_occupancy, name='api_ingest_occupancy'),
]
