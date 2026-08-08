import { useEffect, useRef, useState, useMemo, forwardRef, useImperativeHandle } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

// CARTO Voyager — light, lively, colorful basemap (free, no API key)
const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json';

// District 1, HCMC center
const DEFAULT_CENTER = [106.695, 10.775];
const DEFAULT_ZOOM = 14.5;

// Road-type color palette for debug overlay
const ROAD_TYPE_COLORS = {
  motorway:      '#e63946',
  motorway_link: '#e63946',
  trunk:         '#f4845f',
  trunk_link:    '#f4845f',
  primary:       '#f77f00',
  primary_link:  '#f77f00',
  secondary:     '#fcbf49',
  secondary_link:'#fcbf49',
  tertiary:      '#90be6d',
  tertiary_link: '#90be6d',
  residential:   '#577590',
  living_street: '#a8dadc',
  service:       '#999999',
  unclassified:  '#bbbbbb',
};

const NODE_TYPE_COLORS = {
  network_grid: '#888888',
  snap_poi:     '#e040fb',
};

const MARKER_COLORS = {
  start:       { top: '#51cf66', bottom: '#2b8a3e' },
  destination: { top: '#ff6b6b', bottom: '#fa5252' },
  multi:       { top: '#845ef7', bottom: '#7048e8' },
};

function createPinSvg(type, label) {
  const colors = MARKER_COLORS[type] || MARKER_COLORS.destination;
  const gradId = `pin-grad-${type}-${label}`;

  return `
    <svg width="34" height="44" viewBox="0 0 34 44" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block;cursor:pointer;filter:drop-shadow(0px 4px 6px rgba(0,0,0,0.3));transition:transform 0.2s ease;">
      <defs>
        <linearGradient id="${gradId}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="${colors.top}"/>
          <stop offset="100%" stop-color="${colors.bottom}"/>
        </linearGradient>
      </defs>
      <path d="M17 2C8.71573 2 2 8.71573 2 17C2 27.5 17 42 17 42C17 42 32 27.5 32 17C32 8.71573 25.2843 2 17 2Z" fill="url(#${gradId})" stroke="#ffffff" stroke-width="2.5" stroke-linejoin="round"/>
      <circle cx="17" cy="17" r="10" fill="#ffffff" fill-opacity="0.22"/>
      <text x="17" y="17" font-family="'Inter', sans-serif" font-size="13" font-weight="800" fill="#ffffff" text-anchor="middle" dominant-baseline="central">${label}</text>
    </svg>
  `;
}

function createArrowImageData(color) {
  const canvas = document.createElement('canvas');
  canvas.width = 24;
  canvas.height = 24;
  const ctx = canvas.getContext('2d');

  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(12, 3);
  ctx.lineTo(20, 18);
  ctx.lineTo(12, 14);
  ctx.lineTo(4, 18);
  ctx.closePath();
  ctx.fill();

  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 1.5;
  ctx.stroke();

  return ctx.getImageData(0, 0, 24, 24);
}

function getVisualizationBounds(searchResult, routeMode, nodeCoordsMap) {
  if (!searchResult) return null;

  const isShortestMode = routeMode === 'shortest';
  const pathCoords = isShortestMode
    ? searchResult.shortest_result?.path_coords || []
    : searchResult.fastest_result?.path_coords || [];

  if (!pathCoords || pathCoords.length === 0) return null;

  let minLon = Infinity, maxLon = -Infinity;
  let minLat = Infinity, maxLat = -Infinity;

  const extend = (lon, lat) => {
    if (lon < minLon) minLon = lon;
    if (lon > maxLon) maxLon = lon;
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
  };

  // 1. Include all path coordinates
  pathCoords.forEach(([lon, lat]) => extend(lon, lat));

  // 2. Include all explored nodes coordinates across all legs
  const legs = isShortestMode
    ? searchResult.legs_shortest || []
    : searchResult.legs_fastest || [];

  legs.forEach((leg) => {
    (leg.explored || []).forEach((step) => {
      if (step.node !== undefined && step.node !== null) {
        const coords = nodeCoordsMap.get(step.node);
        if (coords) extend(coords[0], coords[1]);
      }
    });
  });

  if (minLon === Infinity) return null;

  return new maplibregl.LngLatBounds([minLon, minLat], [maxLon, maxLat]);
}

const MapView = forwardRef(function MapView({
  network,
  searchResult,
  routeMode = 'shortest',
  startNode,
  destinations,
  pois,
  animState,
  showDebug,
}, ref) {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const selectedMarkersRef = useRef({});
  const [mapReady, setMapReady] = useState(false);

  // ── Imperative handle for Screenshot export ──────────────────────────
  useImperativeHandle(ref, () => ({
    takeScreenshot: async () => {
      if (!map.current || !mapContainer.current) return;
      const m = map.current;

      // 1. Focus map tightly around route and all explored nodes
      const bounds = getVisualizationBounds(searchResult, routeMode, nodeCoordsMap);
      if (bounds) {
        m.fitBounds(bounds, { padding: 50, animate: false });
      }

      // Force repaint to update canvas buffer immediately
      m.triggerRepaint();

      // Short pause to ensure WebGL canvas and tile rendering completes
      await new Promise((resolve) => setTimeout(resolve, 150));

      const mapCanvas = m.getCanvas();
      const containerEl = mapContainer.current;
      const containerRect = containerEl.getBoundingClientRect();

      const outCanvas = document.createElement('canvas');
      outCanvas.width = mapCanvas.width;
      outCanvas.height = mapCanvas.height;
      const ctx = outCanvas.getContext('2d');

      const scale = outCanvas.width / containerRect.width;

      // Draw map canvas
      ctx.drawImage(mapCanvas, 0, 0);

      // 2. Draw MapLibre Marker DOM overlays
      const markerEls = Array.from(containerEl.querySelectorAll('.maplibregl-marker'));
      for (const markerEl of markerEls) {
        const mRect = markerEl.getBoundingClientRect();
        const x = (mRect.left - containerRect.left) * scale;
        const y = (mRect.top - containerRect.top) * scale;
        const w = mRect.width * scale;
        const h = mRect.height * scale;

        const svgEl = markerEl.querySelector('svg');
        if (svgEl) {
          try {
            const svgString = new XMLSerializer().serializeToString(svgEl);
            const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const img = new Image();
            img.src = url;
            await new Promise((resolve, reject) => {
              img.onload = () => resolve();
              img.onerror = () => reject();
            });
            ctx.drawImage(img, x, y, w, h);
            URL.revokeObjectURL(url);
          } catch (e) {
            console.warn('Failed to render marker SVG onto canvas:', e);
          }
        }
      }

      // 3. Draw Legend Overlay if visible
      const legendEl = containerEl.querySelector('.map-legend');
      if (legendEl) {
        const lRect = legendEl.getBoundingClientRect();
        const lx = (lRect.left - containerRect.left) * scale;
        const ly = (lRect.top - containerRect.top) * scale;
        const lw = lRect.width * scale;
        const lh = lRect.height * scale;

        ctx.save();
        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.shadowColor = 'rgba(0, 0, 0, 0.15)';
        ctx.shadowBlur = 12 * scale;
        ctx.shadowOffsetY = 4 * scale;

        const radius = 12 * scale;
        ctx.beginPath();
        ctx.moveTo(lx + radius, ly);
        ctx.lineTo(lx + lw - radius, ly);
        ctx.quadraticCurveTo(lx + lw, ly, lx + lw, ly + radius);
        ctx.lineTo(lx + lw, ly + lh - radius);
        ctx.quadraticCurveTo(lx + lw, ly + lh, lx + lw - radius, ly + lh);
        ctx.lineTo(lx + radius, ly + lh);
        ctx.quadraticCurveTo(lx, ly + lh, lx, ly + lh - radius);
        ctx.lineTo(lx, ly + radius);
        ctx.quadraticCurveTo(lx, ly, lx + radius, ly);
        ctx.closePath();
        ctx.fill();

        // Legend items
        const items = Array.from(legendEl.querySelectorAll('.map-legend__item'));
        ctx.font = `600 ${Math.round(12 * scale)}px Inter, sans-serif`;
        ctx.textBaseline = 'middle';

        let currentY = ly + 18 * scale;
        for (const item of items) {
          const opacity = item.style.opacity ? parseFloat(item.style.opacity) : 1;
          ctx.globalAlpha = opacity;

          const lineSpan = item.querySelector('.map-legend__line');
          const textSpan = item.querySelector('span:not(.map-legend__line)');

          if (lineSpan) {
            const lineStyle = window.getComputedStyle(lineSpan);
            ctx.fillStyle = lineStyle.backgroundColor || '#2563eb';
            ctx.fillRect(lx + 14 * scale, currentY - 1.5 * scale, 24 * scale, 3 * scale);
          }

          if (textSpan) {
            ctx.fillStyle = '#1a1a2e';
            ctx.fillText(textSpan.textContent, lx + 46 * scale, currentY);
          }

          currentY += 22 * scale;
        }
        ctx.restore();
      }

      // 4. Download file as timestamp
      const now = new Date();
      const pad = (n) => String(n).padStart(2, '0');
      const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;

      const dataUrl = outCanvas.toDataURL('image/png');
      const link = document.createElement('a');
      link.href = dataUrl;
      link.download = `${timestamp}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    },
  }));

  // ── Precompute fast lookup maps for nodes & edges ────────────────────
  const { edgeMap, nodeCoordsMap } = useMemo(() => {
    const eMap = new Map();
    const nMap = new Map();

    if (network?.nodes?.features) {
      network.nodes.features.forEach((f) => {
        nMap.set(f.properties.id, f.geometry.coordinates);
      });
    }

    if (network?.edges?.features) {
      network.edges.features.forEach((f) => {
        const u = f.properties.start_node;
        const v = f.properties.end_node;
        const coords = f.geometry.coordinates;
        eMap.set(`${u}-${v}`, coords);
        eMap.set(`${v}-${u}`, [...coords].reverse());
      });
    }

    return { edgeMap: eMap, nodeCoordsMap: nMap };
  }, [network]);

  // ── Initialise map ──────────────────────────────────────────────────
  useEffect(() => {
    if (map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: MAP_STYLE,
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      pitch: 0,
      attributionControl: false,
      preserveDrawingBuffer: true,
    });

    map.current.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.current.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');

    map.current.on('load', () => {
      const m = map.current;
      if (!m.hasImage('arrow-blue')) m.addImage('arrow-blue', createArrowImageData('#4a90d9'));
      if (!m.hasImage('arrow-red')) m.addImage('arrow-red', createArrowImageData('#ff6b6b'));
      if (!m.hasImage('arrow-gray')) m.addImage('arrow-gray', createArrowImageData('#555555'));

      // Find actual text label layer from the basemap, or append to top if not found
      const baseLabelLayer = m.getStyle().layers.find(
        (l) => l.type === 'symbol' && l.layout && l.layout['text-field']
      );
      const beforeId = baseLabelLayer?.id;

      const emptyLine = { type: 'Feature', geometry: { type: 'LineString', coordinates: [] } };
      const emptyFC = { type: 'FeatureCollection', features: [] };

      // ── Pre-create: explored-edges (gray search tree) ──
      m.addSource('explored-edges', { type: 'geojson', data: emptyFC });
      m.addLayer({
        id: 'explored-edges-layer', type: 'line', source: 'explored-edges',
        paint: { 'line-color': '#777777', 'line-width': 3, 'line-opacity': 0.75 },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      });

      // ── Pre-create: explored-points (colored circles) ──
      m.addSource('explored-points', { type: 'geojson', data: emptyFC });
      m.addLayer({
        id: 'explored-points-layer', type: 'circle', source: 'explored-points',
        paint: {
          'circle-radius': 4,
          'circle-color': ['interpolate', ['linear'], ['get', 'order'], 0, '#51cf66', 50, '#fcc419', 100, '#ff6b6b'],
          'circle-opacity': 0.8,
        },
      });

      // ── Pre-create: snap-poi-lines (dashed magenta) ──
      m.addSource('snap-poi-lines', { type: 'geojson', data: emptyFC });
      m.addLayer({
        id: 'snap-poi-lines-layer', type: 'line', source: 'snap-poi-lines',
        paint: { 'line-color': '#e040fb', 'line-width': 3, 'line-dasharray': [3, 3], 'line-opacity': 0.9 },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      });

      // ── Pre-create: fastest-route (red line + arrows) ──
      m.addSource('fastest-route', { type: 'geojson', data: emptyLine });
      m.addLayer({
        id: 'fastest-route-layer', type: 'line', source: 'fastest-route',
        paint: { 'line-color': '#ff3333', 'line-width': 6, 'line-opacity': 0.9 },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      });
      m.addLayer({
        id: 'fastest-route-arrows', type: 'symbol', source: 'fastest-route',
        layout: {
          'symbol-placement': 'line', 'symbol-spacing': 60,
          'icon-image': 'arrow-red', 'icon-size': 0.65,
          'icon-allow-overlap': true, 'icon-ignore-placement': true,
          'icon-keep-upright': false, 'icon-rotation-alignment': 'line',
        },
      });

      // ── Pre-create: shortest-route (blue line + arrows — topmost route) ──
      m.addSource('shortest-route', { type: 'geojson', data: emptyLine });
      m.addLayer({
        id: 'shortest-route-layer', type: 'line', source: 'shortest-route',
        paint: { 'line-color': '#2563eb', 'line-width': 6, 'line-opacity': 0.95 },
        layout: { 'line-cap': 'round', 'line-join': 'round' },
      });
      m.addLayer({
        id: 'shortest-route-arrows', type: 'symbol', source: 'shortest-route',
        layout: {
          'symbol-placement': 'line', 'symbol-spacing': 60,
          'icon-image': 'arrow-blue', 'icon-size': 0.65,
          'icon-allow-overlap': true, 'icon-ignore-placement': true,
          'icon-keep-upright': false, 'icon-rotation-alignment': 'line',
        },
      });

      setMapReady(true);
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  // ── Selected Location Markers (Start & Destinations) ────────────────
  useEffect(() => {
    if (!mapReady || !map.current) return;

    const findPoi = (id) => pois?.find((p) => p.id === id);
    const desiredMarkers = {};

    // 1. Start marker
    if (startNode !== null) {
      const p = findPoi(startNode);
      if (p) {
        desiredMarkers[startNode] = {
          id: startNode,
          type: 'start',
          label: 'S',
          roleName: 'Start Location',
          name: p.name,
          lat: p.lat,
          lon: p.lon,
        };
      }
    }

    // 2. Destination markers
    const validDests = (destinations || []).filter((d) => d !== null);
    const isMulti = validDests.length > 1;
    const visitingOrder = searchResult?.visiting_order;

    validDests.forEach((destId, idx) => {
      const p = findPoi(destId);
      if (!p) return;

      let label = 'D';
      let roleName = 'Destination';
      let type = 'destination';

      if (isMulti) {
        type = 'multi';
        let orderIndex = idx + 1;
        if (visitingOrder && Array.isArray(visitingOrder)) {
          const vIdx = visitingOrder.indexOf(destId);
          if (vIdx >= 0) orderIndex = vIdx + 1;
        }
        label = `${orderIndex}`;
        roleName = `Stop ${orderIndex}`;
      }

      desiredMarkers[destId] = {
        id: destId,
        type,
        label,
        roleName,
        name: p.name,
        lat: p.lat,
        lon: p.lon,
      };
    });

    const currentMarkers = selectedMarkersRef.current;

    // Remove markers for locations no longer selected
    Object.keys(currentMarkers).forEach((idStr) => {
      const id = parseInt(idStr);
      if (!desiredMarkers[id]) {
        currentMarkers[id].marker.remove();
        delete currentMarkers[id];
      }
    });

    // Add or update markers
    Object.values(desiredMarkers).forEach((item) => {
      const existing = currentMarkers[item.id];
      const key = `${item.type}-${item.label}`;

      if (existing) {
        if (existing.key !== key) {
          existing.el.innerHTML = createPinSvg(item.type, item.label);
          existing.popup.setHTML(`
            <div class="marker-popup">
              <div class="marker-popup__role marker-popup__role--${item.type}">${item.roleName}</div>
              <div class="marker-popup__title">${item.name}</div>
            </div>
          `);
          existing.key = key;
        }
      } else {
        const el = document.createElement('div');
        el.style.cursor = 'pointer';
        el.innerHTML = createPinSvg(item.type, item.label);

        // Hover scale animation
        el.addEventListener('mouseenter', () => {
          const svg = el.querySelector('svg');
          if (svg) svg.style.transform = 'scale(1.15)';
        });
        el.addEventListener('mouseleave', () => {
          const svg = el.querySelector('svg');
          if (svg) svg.style.transform = 'scale(1)';
        });

        const popup = new maplibregl.Popup({ offset: [0, -35], closeButton: false }).setHTML(`
          <div class="marker-popup">
            <div class="marker-popup__role marker-popup__role--${item.type}">${item.roleName}</div>
            <div class="marker-popup__title">${item.name}</div>
          </div>
        `);

        const marker = new maplibregl.Marker({ element: el, anchor: 'bottom' })
          .setLngLat([item.lon, item.lat])
          .setPopup(popup)
          .addTo(map.current);

        currentMarkers[item.id] = { marker, popup, el, key };
      }
    });
  }, [mapReady, startNode, destinations, pois, searchResult]);

  // ── Auto-focus map when Start or Destination is selected / changed ───
  const prevSelectedRef = useRef({ startNode: null, destinations: [] });

  useEffect(() => {
    if (!mapReady || !map.current || !pois || pois.length === 0) return;

    const findPoi = (id) => pois.find((p) => p.id === id);

    let targetId = null;

    if (startNode !== null && startNode !== prevSelectedRef.current.startNode) {
      targetId = startNode;
    } else {
      const prevDests = prevSelectedRef.current.destinations || [];
      const currDests = destinations || [];
      for (let i = 0; i < Math.max(currDests.length, prevDests.length); i++) {
        if (currDests[i] !== null && currDests[i] !== prevDests[i]) {
          targetId = currDests[i];
          break;
        }
      }
    }

    prevSelectedRef.current = {
      startNode,
      destinations: [...(destinations || [])],
    };

    if (targetId !== null) {
      const p = findPoi(targetId);
      if (p && p.lat !== undefined && p.lon !== undefined) {
        map.current.flyTo({
          center: [p.lon, p.lat],
          zoom: 16,
          duration: 800,
        });
      }
    }
  }, [mapReady, startNode, destinations, pois]);

  // ── Debug overlay: edges by road type ───────────────────────────────
  useEffect(() => {
    if (!mapReady || !network) return;
    const m = map.current;

    const edgeSourceId = 'debug-edges';
    const edgeLayerId = 'debug-edges-layer';
    const nodeSourceId = 'debug-nodes';
    const nodeLayerId = 'debug-nodes-layer';
    const poiNodeLayerId = 'debug-poi-nodes-layer';

    if (showDebug) {
      // ── Add edges with road-type colors ──
      if (!m.getSource(edgeSourceId)) {
        m.addSource(edgeSourceId, {
          type: 'geojson',
          data: network.edges,
        });
      }
      if (!m.getLayer(edgeLayerId)) {
        // Build a match expression for road_type -> color
        const matchExpr = ['match', ['get', 'road_type']];
        for (const [rt, color] of Object.entries(ROAD_TYPE_COLORS)) {
          matchExpr.push(rt, color);
        }
        matchExpr.push('#cccccc'); // fallback

        m.addLayer({
          id: edgeLayerId,
          type: 'line',
          source: edgeSourceId,
          paint: {
            'line-color': matchExpr,
            'line-width': 2,
            'line-opacity': 0.85,
          },
          layout: {
            'line-cap': 'round',
            'line-join': 'round',
          },
        });
      }

      // ── Add debug directional arrows along edges ──
      if (!m.getLayer('debug-edges-arrows')) {
        m.addLayer({
          id: 'debug-edges-arrows',
          type: 'symbol',
          source: edgeSourceId,
          layout: {
            'symbol-placement': 'line',
            'symbol-spacing': 90,
            'icon-image': 'arrow-gray',
            'icon-size': 0.5,
            'icon-allow-overlap': true,
            'icon-keep-upright': false,
            'icon-rotation-alignment': 'line',
          },
        });
      }

      // ── Add nodes with type colors ──
      if (!m.getSource(nodeSourceId)) {
        m.addSource(nodeSourceId, {
          type: 'geojson',
          data: network.nodes,
        });
      }
      if (!m.getLayer(nodeLayerId)) {
        m.addLayer({
          id: nodeLayerId,
          type: 'circle',
          source: nodeSourceId,
          filter: ['!=', ['get', 'type'], 'snap_poi'],
          paint: {
            'circle-radius': 2.5,
            'circle-color': NODE_TYPE_COLORS.network_grid,
            'circle-opacity': 0.6,
          },
        });
      }
      if (!m.getLayer(poiNodeLayerId)) {
        m.addLayer({
          id: poiNodeLayerId,
          type: 'circle',
          source: nodeSourceId,
          filter: ['==', ['get', 'type'], 'snap_poi'],
          paint: {
            'circle-radius': 5,
            'circle-color': NODE_TYPE_COLORS.snap_poi,
            'circle-stroke-color': '#ffffff',
            'circle-stroke-width': 1.5,
            'circle-opacity': 1,
          },
        });
      }
    } else {
      // Remove debug layers
      if (m.getLayer(poiNodeLayerId)) m.removeLayer(poiNodeLayerId);
      if (m.getLayer(nodeLayerId)) m.removeLayer(nodeLayerId);
      if (m.getLayer('debug-edges-arrows')) m.removeLayer('debug-edges-arrows');
      if (m.getLayer(edgeLayerId)) m.removeLayer(edgeLayerId);
      if (m.getSource(nodeSourceId)) m.removeSource(nodeSourceId);
      if (m.getSource(edgeSourceId)) m.removeSource(edgeSourceId);
    }
  }, [mapReady, network, showDebug]);

  // ── 1. Update POI-to-snap dashed lines (source pre-created on load) ──
  useEffect(() => {
    if (!mapReady || !map.current) return;
    const m = map.current;

    const activePoiIds = [startNode, ...(destinations || [])].filter((id) => id !== null);
    const snapLineFeatures = [];

    activePoiIds.forEach((poiId) => {
      const p = pois?.find((item) => item.id === poiId);
      if (p && p.snap_lat !== undefined && p.snap_lon !== undefined) {
        const distSq = (p.lon - p.snap_lon) ** 2 + (p.lat - p.snap_lat) ** 2;
        if (distSq > 1e-10) {
          snapLineFeatures.push({
            type: 'Feature',
            geometry: {
              type: 'LineString',
              coordinates: [[p.lon, p.lat], [p.snap_lon, p.snap_lat]],
            },
            properties: { name: p.name },
          });
        }
      }
    });

    m.getSource('snap-poi-lines')?.setData({ type: 'FeatureCollection', features: snapLineFeatures });
  }, [mapReady, startNode, destinations, pois]);

  // ── 2. Update Shortest & Fastest Route data based on routeMode ──
  useEffect(() => {
    if (!mapReady || !map.current) return;
    const m = map.current;

    const emptyLine = { type: 'Feature', geometry: { type: 'LineString', coordinates: [] } };

    if (!searchResult) {
      m.getSource('shortest-route')?.setData(emptyLine);
      m.getSource('fastest-route')?.setData(emptyLine);
      return;
    }

    const isShortestMode = routeMode === 'shortest';

    // Get path coordinates for active route or during step-by-step animation
    let activeCoords = [];
    if (animState && animState.isAnimating && animState.completedLegsCoords !== null) {
      animState.completedLegsCoords.forEach((legCoords) => {
        if (!legCoords || legCoords.length === 0) return;
        if (activeCoords.length === 0) {
          activeCoords.push(...legCoords);
        } else {
          activeCoords.push(...legCoords.slice(1));
        }
      });
    } else {
      activeCoords = isShortestMode
        ? searchResult.shortest_result?.path_coords || []
        : searchResult.fastest_result?.path_coords || [];
    }

    if (isShortestMode) {
      // Draw Shortest route (blue), clear Fastest route
      m.getSource('shortest-route')?.setData({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: activeCoords.length >= 2 ? activeCoords : [] },
      });
      m.getSource('fastest-route')?.setData(emptyLine);
    } else {
      // Draw Fastest route (red), clear Shortest route
      m.getSource('fastest-route')?.setData({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: activeCoords.length >= 2 ? activeCoords : [] },
      });
      m.getSource('shortest-route')?.setData(emptyLine);
    }

    // Fit map bounds on initial search result arrival or route mode switch
    if (!animState || !animState.isAnimating) {
      const bounds = getVisualizationBounds(searchResult, routeMode, nodeCoordsMap);
      if (bounds) {
        m.fitBounds(bounds, { padding: 50, duration: 800 });
      }
    }
  }, [mapReady, searchResult, routeMode, animState?.completedLegsCoords, animState?.isAnimating]);

  // ── 3. Update explored edges + nodes data (sources pre-created on load) ──
  useEffect(() => {
    if (!mapReady || !map.current) return;
    const m = map.current;

    const activeEdges = animState?.activeExploredEdges || [];
    const activeNodes = animState?.activeExploredNodes || [];

    // ── Explored Search Tree Edges ──
    const edgeFeatures = activeEdges
      .map(({ parent, node }) => {
        if (parent === null || parent === undefined) return null;
        let coords = edgeMap.get(`${parent}-${node}`);
        if (!coords) {
          const uPt = nodeCoordsMap.get(parent);
          const vPt = nodeCoordsMap.get(node);
          if (uPt && vPt) coords = [uPt, vPt];
        }
        if (!coords) return null;
        return { type: 'Feature', geometry: { type: 'LineString', coordinates: coords } };
      })
      .filter(Boolean);

    m.getSource('explored-edges')?.setData({ type: 'FeatureCollection', features: edgeFeatures });

    // ── Explored Nodes (Circles) ──
    const nodeFeatures = activeNodes
      .map((nodeId, i) => {
        const coords = nodeCoordsMap.get(nodeId);
        if (!coords) return null;
        return { type: 'Feature', geometry: { type: 'Point', coordinates: coords }, properties: { order: i } };
      })
      .filter(Boolean);

    m.getSource('explored-points')?.setData({ type: 'FeatureCollection', features: nodeFeatures });
  }, [mapReady, animState, edgeMap, nodeCoordsMap]);

  // ── Collect visible road types for legend ────────────────────────────
  const visibleRoadTypes = [];
  if (showDebug && network?.edges?.features) {
    const seen = new Set();
    for (const f of network.edges.features) {
      const rt = f.properties.road_type;
      if (rt && !seen.has(rt)) {
        seen.add(rt);
        visibleRoadTypes.push(rt);
      }
    }
    visibleRoadTypes.sort();
  }

  return (
    <div className="app__map">
      <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />

      {/* Route legend */}
      {searchResult && !showDebug && (
        <div className="map-legend">
          <div className={`map-legend__item ${routeMode === 'shortest' ? 'map-legend__item--active' : ''}`} style={{ opacity: routeMode === 'shortest' ? 1 : 0.4 }}>
            <span className="map-legend__line map-legend__line--shortest" />
            <span>Shortest route {routeMode === 'shortest' ? '(Active)' : ''}</span>
          </div>
          <div className={`map-legend__item ${routeMode === 'fastest' ? 'map-legend__item--active' : ''}`} style={{ opacity: routeMode === 'fastest' ? 1 : 0.4 }}>
            <span className="map-legend__line map-legend__line--fastest" />
            <span>Fastest route {routeMode === 'fastest' ? '(Active)' : ''}</span>
          </div>
        </div>
      )}

      {/* Debug legend */}
      {showDebug && (
        <div className="map-legend map-legend--debug">
          <div style={{ fontWeight: 700, fontSize: '12px', marginBottom: '4px', color: '#1a1a2e' }}>
            🛣️ Road Types
          </div>
          {visibleRoadTypes.map((rt) => (
            <div className="map-legend__item" key={rt}>
              <span
                className="map-legend__line"
                style={{ background: ROAD_TYPE_COLORS[rt] || '#cccccc' }}
              />
              <span>{rt}</span>
            </div>
          ))}
          <div style={{ borderTop: '1px solid rgba(0,0,0,0.08)', margin: '6px 0', paddingTop: '6px', fontWeight: 700, fontSize: '12px', color: '#1a1a2e' }}>
            📍 Node Types
          </div>
          <div className="map-legend__item">
            <span
              style={{
                width: '10px', height: '10px', borderRadius: '50%',
                background: NODE_TYPE_COLORS.network_grid, display: 'inline-block',
              }}
            />
            <span>Network node</span>
          </div>
          <div className="map-legend__item">
            <span
              style={{
                width: '10px', height: '10px', borderRadius: '50%',
                background: NODE_TYPE_COLORS.snap_poi,
                border: '1.5px solid white',
                boxShadow: '0 0 3px rgba(0,0,0,0.2)',
                display: 'inline-block',
              }}
            />
            <span>POI (snap) node</span>
          </div>
        </div>
      )}
    </div>
  );
});

export default MapView;

