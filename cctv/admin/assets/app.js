const API_EVENTS = 'api_events.php?limit=20';
const BASE_LIVE_FEED = 'http://localhost:8000/api/camera/feed';

async function fetchEvents() {
  try {
    const res = await fetch(API_EVENTS);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'API error');
    renderEvents(data.events);
  } catch (err) {
    console.error('Failed to fetch events', err);
    document.getElementById('eventsList').innerText = 'Failed to load events.';
  }
}

function renderEvents(events) {
  const list = document.getElementById('eventsList');
  if (!events || events.length === 0) {
    list.innerHTML = '<div class="text-muted">No events yet.</div>';
    showSelectedEvent(null);
    return;
  }

  let html = '<div class="list-group">';
  events.forEach((e, idx) => {
    const thumb = e.image_url ? `<img src="${e.image_url}" class="me-2" style="width:64px;height:48px;object-fit:cover;">` : '';
    const cameraInfo = e.camera_name ? `${e.camera_name}${e.camera_location ? ` | ${e.camera_location}` : ''}` : e.camera_id ? `Camera ${e.camera_id}` : '';
    html += `
      <button type="button" class="list-group-item list-group-item-action d-flex align-items-center" onclick="showEvent(${idx})">
        ${thumb}
        <div>
          <div class="fw-bold">${e.event_type}</div>
          <div class="small text-muted">${e.timestamp}${cameraInfo ? ` | ${cameraInfo}` : ''}</div>
          ${cameraInfo ? `<div class="small text-secondary">${cameraInfo}</div>` : ''}
          <div class="small text-muted">${e.details || ''}</div>
        </div>
      </button>
    `;
  });
  html += '</div>';
  list.innerHTML = html;

  // Show first event as live preview by default
  showSelectedEvent(events[0]);
  window.__events = events;
}

function showSelectedEvent(event) {
  const title = document.getElementById('alertTitle');
  const meta = document.getElementById('alertMeta');
  const cameraLabel = document.getElementById('alertCamera');
  const cameraLocation = document.getElementById('alertLocation');
  const alertTime = document.getElementById('alertTime');
  const details = document.getElementById('alertDetails');
  const image = document.getElementById('liveImage');
  const feed = document.getElementById('cameraFeed');
  const feedInfo = document.getElementById('feedInfo');

  if (!event) {
    title.innerText = 'No recent alerts';
    meta.innerText = 'Select an event to see details.';
    cameraLabel.innerText = 'N/A';
    cameraLocation.innerText = 'N/A';
    alertTime.innerText = 'N/A';
    details.innerText = 'No event message available.';
    image.src = 'https://via.placeholder.com/640x480?text=No+Image';
    feed.src = 'https://via.placeholder.com/640x480?text=Select+an+event+to+view+live+feed';
    feedInfo.innerText = 'Live feed will appear here after selecting a camera event.';
    return;
  }

  const cameraInfo = event.camera_name || event.camera_id || 'Unknown';
  title.innerText = `${event.event_type} detected`;
  meta.innerText = `${event.timestamp}`;
  cameraLabel.innerText = event.camera_name || event.camera_id || 'Unknown';
  cameraLocation.innerText = event.camera_location || 'Unknown';
  alertTime.innerText = event.timestamp;
  details.innerText = event.details || 'No details available.';

  if (event.image_url) {
    image.src = event.image_url;
  } else {
    image.src = 'https://via.placeholder.com/640x480?text=No+Image';
  }

  if (event.camera_id) {
    feed.src = `${BASE_LIVE_FEED}?camera_id=${encodeURIComponent(event.camera_id)}`;
    feedInfo.innerText = `Live feed from ${cameraInfo}`;
  } else {
    feed.src = 'https://via.placeholder.com/640x480?text=Live+feed+not+available';
    feedInfo.innerText = 'Live feed is not available for this event.';
  }
}

function showEvent(index) {
  const e = window.__events && window.__events[index];
  if (!e) return;
  showSelectedEvent(e);
}

fetchEvents();
setInterval(fetchEvents, 3000);
