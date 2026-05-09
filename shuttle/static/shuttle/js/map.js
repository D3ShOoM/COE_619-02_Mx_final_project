const state = {
  map: null,
  routeLine: null,
  stopMarkers: {},
  busMarkers: {},
  stops: [],
  shape: [],
};

async function getJSON(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`${url} -> ${response.status}`);
  return response.json();
}

function fmtAge(seconds) {
  if (seconds === null || seconds === undefined) return 'never';
  if (seconds < 60) return `${seconds.toFixed(0)}s ago`;
  return `${(seconds / 60).toFixed(1)}m ago`;
}

function badge(level) {
  return `<span class="badge ${level}">${level}</span>`;
}

function ensureMap(stopsData) {
  state.stops = stopsData.stops || [];
  state.shape = stopsData.shape || [];
  if (!window.L) {
    document.getElementById('map').hidden = true;
    document.getElementById('fallbackMap').hidden = false;
    renderFallbackStops();
    return;
  }
  if (state.map) return;
  const center = state.stops.length ? [state.stops[0].lat, state.stops[0].lon] : [26.309, 50.148];
  state.map = L.map('map', { zoomControl: true }).setView(center, 15);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(state.map);
  if (state.shape.length) {
    state.routeLine = L.polyline(state.shape.map(p => [p.lat, p.lon]), {color:stopsData.route.color||'#2563eb' , weight: 6, opacity: 0.75 }).addTo(state.map);
    state.map.fitBounds(state.routeLine.getBounds(), { padding: [30, 30] });
  }
  state.stops.forEach(stop => {
    state.stopMarkers[stop.stop_id] = L.circleMarker([stop.lat, stop.lon], {
      color:stopsData.route.color||'#2563eb', fillColor:stopsData.route.color||'#2563eb',radius: 8, weight: 3, fillOpacity: 1
    }).addTo(state.map).bindPopup(`<strong>${stop.sequence}. ${stop.name}</strong><br>${stop.stop_id}`);
  });
}

function renderFallbackStops() {
  const holder = document.getElementById('fallbackStops');
  if (!holder) return;
  const coords = [[120,245],[285,95],[450,155],[445,300]];
  holder.innerHTML = state.stops.map((stop, idx) => {
    const [x, y] = coords[idx] || [120 + idx * 80, 200];
    return `<g><circle class="stop-dot" cx="${x}" cy="${y}" r="12"></circle><text x="${x+16}" y="${y+5}" font-size="16" fill="#14221a">${stop.name}</text></g>`;
  }).join('');
}

function renderFallbackBuses(vehicles) {
  const holder = document.getElementById('fallbackBuses');
  if (!holder) return;
  holder.innerHTML = vehicles.map((bus, idx) => {
    const angle = (bus.progress_m || 0) / 1400 * Math.PI * 2 + idx;
    const x = 320 + Math.cos(angle) * 190;
    const y = 205 + Math.sin(angle) * 105;
    return `<g><circle class="bus-dot" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="14"></circle><text x="${x+18}" y="${y+5}" font-size="15" font-weight="700" fill="#14221a">${bus.bus_id}</text></g>`;
  }).join('');
}

function updateVehicleMarkers(vehicles) {
  if (!window.L || !state.map) {
    renderFallbackBuses(vehicles);
    return;
  }

  vehicles.forEach(bus => {
    if (bus.lat === null || bus.lon === null) return;
    const BUS_ICON_URLS = {
            "BUS-01": "static/shuttle/img/bus1.png",
            "BUS-02": "static/shuttle/img/bus2.png"
        };
    const iconUrl = BUS_ICON_URLS?.[bus.bus_id];
    const icon = iconUrl
      ? L.icon({
          iconUrl: iconUrl,
          iconSize: [42, 42],
          iconAnchor: [21, 21],
          popupAnchor: [0, -20],
        })
      : L.divIcon({
          html: `<div class="bus-marker">${bus.bus_id.replace('BUS-', '')}</div>`,
          className: 'bus-icon',
          iconSize: [34, 34],
        });

    const popup = `
      <strong>${bus.label}</strong><br>
      Speed: ${bus.speed_kmh} km/h<br>
      Occupancy: ${bus.occupancy_count}/${bus.capacity} ${badge(bus.occupancy_level)}<br>
      Last seen: ${fmtAge(bus.seconds_since_seen)}
    `;

    if (!state.busMarkers[bus.bus_id]) {
      state.busMarkers[bus.bus_id] = L.marker([bus.lat, bus.lon], { icon })
        .addTo(state.map)
        .bindPopup(popup);
    } else {
      state.busMarkers[bus.bus_id]
        .setLatLng([bus.lat, bus.lon])
        .setIcon(icon)
        .setPopupContent(popup);
    }
  });
}

function renderVehicleTable(vehicles) {
  const tbody = document.getElementById('vehicleTable');
  tbody.innerHTML = vehicles.map(bus => `
    <tr>
      <td><strong>${bus.bus_id}</strong><br><small>${bus.label}</small></td>
      <td>${bus.speed_kmh} km/h</td>
      <td>${bus.occupancy_count}/${bus.capacity} ${badge(bus.occupancy_level)}</td>
      <td>${fmtAge(bus.seconds_since_seen)}</td>
      <td><span class="badge ${bus.online ? 'online' : 'stale'}">${bus.online ? 'ONLINE' : 'STALE'}</span></td>
    </tr>
  `).join('') || '<tr><td colspan="5">No vehicles seeded. Run python manage.py seed_demo.</td></tr>';
}

function renderEtaBoard(tripUpdates) {
  const board = document.getElementById('etaBoard');
  const entities = tripUpdates.entity || [];
  board.innerHTML = entities.map(entity => {
    const update = entity.trip_update;
    const rows = (update.stop_time_update || []).slice(0, 4).map(stop => `
      <div class="line"><span>${stop.stop_name}</span><strong>${stop.eta_minutes} min</strong></div>
    `).join('');
    return `<article class="eta-card"><h3>${update.vehicle.label} ${badge(update.occupancy_status)}</h3>${rows}</article>`;
  }).join('') || '<p>No ETA data yet. Run seed_demo.</p>';
}

async function refresh() {
  try {
    const [stops, vehicles, trips, health] = await Promise.all([
      getJSON('/api/stops/'),
      getJSON('/api/vehicles/'),
      getJSON('/api/gtfs-rt/trip-updates/'),
      getJSON('/api/feed-health/'),
    ]);
    ensureMap(stops);
    updateVehicleMarkers(vehicles.vehicles || []);
    renderVehicleTable(vehicles.vehicles || []);
    renderEtaBoard(trips);
    document.getElementById('feedStatus').textContent = health.status;
    document.getElementById('feedFreshness').textContent = health.feed_freshness_seconds === null ? 'No pings yet' : `${health.feed_freshness_seconds}s freshness`;
    document.getElementById('vehicleCount').textContent = `${health.online_vehicle_count}/${health.vehicle_count}`;
    document.getElementById('lastUpdated').textContent = new Date().toLocaleTimeString();
  } catch (error) {
    console.error(error);
    document.getElementById('lastUpdated').textContent = 'API error';
  }
}

refresh();
setInterval(refresh, 3000);
