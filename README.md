# Campus Shuttle Django Demo

A runnable Django demo for **Campus Shuttle: Privacy-Preserving Bus Occupancy & Real-Time ETA (GTFS-RT)**.


## What the demo includes

- Django app with SQLite by default for quick local demos.
- Seeded 4-stop KFUPM-style campus pilot loop.
- Two simulated buses that continuously move around the route.
- GTFS-RT-like JSON endpoints for VehiclePositions and TripUpdates.
- Segment-based ETA estimation with a lightweight Kalman update helper.
- Occupancy state/level logic: Low, Medium, High, derived from counts and capacity thresholds.
- Rider-facing live map page.
- Admin/operations dashboard for bus last-seen, feed freshness, occupancy, and logs.
- Device ingestion endpoints for future GNSS and occupancy sensor integration.
- Demo script and API reference in `docs/`.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open:

- Rider map: <http://127.0.0.1:8000/>
- Operator dashboard: <http://127.0.0.1:8000/dashboard/>
- API docs page: <http://127.0.0.1:8000/api-docs/>
- Django admin: <http://127.0.0.1:8000/admin/>

The demo auto-simulates buses during API requests, so `runserver` is enough. For a more realistic continuous feed, run this in another terminal:

```bash
python manage.py simulate_buses --interval 2
```

## Create an admin user

```bash
python manage.py createsuperuser
```

## Useful API endpoints

```bash
curl http://127.0.0.1:8000/api/stops/
curl http://127.0.0.1:8000/api/vehicles/
curl http://127.0.0.1:8000/api/gtfs-rt/vehicle-positions/
curl http://127.0.0.1:8000/api/gtfs-rt/trip-updates/
curl http://127.0.0.1:8000/api/feed-health/
```

Example GNSS ingestion:

```bash
curl -X POST http://127.0.0.1:8000/api/ingest/gps/ \
  -H "Content-Type: application/json" \
  -d '{"bus_id":"BUS-01","lat":26.3074,"lon":50.1492,"speed_mps":5.2,"heading":87,"source":"device-demo"}'
```

Example occupancy ingestion:

```bash
curl -X POST http://127.0.0.1:8000/api/ingest/occupancy/ \
  -H "Content-Type: application/json" \
  -d '{"bus_id":"BUS-01","count":18,"boardings":3,"alightings":1,"source":"dual-ir-demo"}'
```

## Project structure

```text
campus_shuttle_demo/
├── campus_shuttle_demo/      # Django settings and root URLs
├── shuttle/                  # Core app: models, API views, services, templates, static files
├── docs/                     # Demo script, API reference, architecture notes
├── manage.py
├── requirements.txt
└── README.md
```

## Reset demo data

```bash
python manage.py reset_demo --yes
python manage.py seed_demo
```
