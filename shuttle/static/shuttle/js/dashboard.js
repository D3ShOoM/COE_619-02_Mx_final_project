async function getJSON(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`${url} -> ${response.status}`);
  return response.json();
}

function fmtAge(seconds) {
  if (seconds === null || seconds === undefined) return 'never';
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  return `${(seconds / 60).toFixed(1)}m`;
}

function badge(level) {
  return `<span class="badge ${level}">${level}</span>`;
}

async function refreshDashboard() {
  try {
    const [health, vehicles, logs] = await Promise.all([
      getJSON('/api/feed-health/'),
      getJSON('/api/vehicles/'),
      getJSON('/api/logs/?limit=16'),
    ]);
    document.getElementById('dashStatus').textContent = health.status;
    document.getElementById('dashTimestamp').textContent = new Date(health.timestamp).toLocaleTimeString();
    document.getElementById('dashOnline').textContent = `${health.online_vehicle_count}`;
    document.getElementById('dashVehicleCount').textContent = `${health.vehicle_count} total vehicles`;
    document.getElementById('dashFreshness').textContent = health.feed_freshness_seconds === null ? '-' : health.feed_freshness_seconds;
    document.getElementById('dashPings').textContent = health.position_ping_count;

    document.getElementById('dashFleet').innerHTML = (vehicles.vehicles || []).map(bus => `
      <tr>
        <td><strong>${bus.bus_id}</strong><br><small>${bus.label}</small></td>
        <td>${bus.route_id}</td>
        <td>${bus.progress_m} m</td>
        <td>${bus.speed_kmh} km/h</td>
        <td>${bus.occupancy_count}/${bus.capacity} ${badge(bus.occupancy_level)}</td>
        <td>${fmtAge(bus.seconds_since_seen)}</td>
      </tr>
    `).join('') || '<tr><td colspan="6">No vehicles seeded.</td></tr>';

    document.getElementById('eventLog').innerHTML = (logs.events || []).map(event => `
      <div class="event">
        <strong>[${event.level}] ${event.component}</strong>
        <span>${event.message}</span><br>
        <small>${new Date(event.created_at).toLocaleString()}</small>
      </div>
    `).join('') || 'No events yet.';
  } catch (error) {
    console.error(error);
    document.getElementById('dashStatus').textContent = 'ERROR';
  }
}

refreshDashboard();
setInterval(refreshDashboard, 4000);
