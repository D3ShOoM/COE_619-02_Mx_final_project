# API Reference

Base URL during local development: `http://127.0.0.1:8000`.

## Stops and route

`GET /api/stops/`

Returns route metadata, shape points, and active stops.

## Vehicles

`GET /api/vehicles/`

Returns latest state for each active bus.

## GTFS-RT-style JSON

`GET /api/gtfs-rt/vehicle-positions/`

Returns `header` and `entity[]` records with GTFS-Realtime-like VehiclePositions fields.

`GET /api/gtfs-rt/trip-updates/`

Returns `header` and `entity[]` records with TripUpdates-like stop arrival estimates.

## Health and logs

`GET /api/feed-health/`

Returns vehicle counts, feed freshness, target update cadence, position ping count, and status.

`GET /api/logs/?limit=20`

Returns recent system events.

## Ingestion

`POST /api/ingest/gps/`

```json
{
  "bus_id": "BUS-01",
  "lat": 26.3074,
  "lon": 50.1492,
  "speed_mps": 5.2,
  "heading": 87,
  "source": "device-demo"
}
```

`POST /api/ingest/occupancy/`

```json
{
  "bus_id": "BUS-01",
  "count": 18,
  "boardings": 3,
  "alightings": 1,
  "source": "dual-ir-demo"
}
```

When `count` is omitted, the endpoint applies `boardings - alightings` to the current count.
