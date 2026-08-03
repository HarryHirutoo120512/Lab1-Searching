const API_BASE = '/api';

export async function fetchLocations() {
  const res = await fetch(`${API_BASE}/locations`);
  if (!res.ok) throw new Error('Failed to fetch locations');
  return res.json();
}

export async function fetchNetwork() {
  const res = await fetch(`${API_BASE}/network`);
  if (!res.ok) throw new Error('Failed to fetch network');
  return res.json();
}

export async function searchRoutes({ algorithm, startNode, destinations }) {
  const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      algorithm,
      start_node: startNode,
      destinations,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Search failed');
  }
  return res.json();
}
