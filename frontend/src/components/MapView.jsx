import { useEffect, useRef, useState, useMemo } from 'react';
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

export default function MapView({
  network,
  searchResult,
  startNode,
  destinations,
  pois,
  animState,
  showDebug,
}) {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const selectedMarkersRef = useRef({});
  const [mapReady, setMapReady] = useState(false);

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
    });

    map.current.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.current.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');

    map.current.on('load', () => {
      if (!map.current.hasImage('arrow-blue')) {
        map.current.addImage('arrow-blue', createArrowImageData('#4a90d9'));
      }
      if (!map.current.hasImage('arrow-red')) {
        map.current.addImage('arrow-red', createArrowImageData('#ff6b6b'));
      }
      if (!map.current.hasImage('arrow-gray')) {
        map.current.addImage('arrow-gray', createArrowImageData('#555555'));
      }
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

  // ── 1. Persistent POI-to-snap dashed lines effect (no flicker) ───────
  useEffect(() => {
    if (!mapReady || !map.current) return;
    const m = map.current;

    const sourceId = 'snap-poi-lines';
    const layerId = 'snap-poi-lines-layer';

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
              coordinates: [
                [p.lon, p.lat],
                [p.snap_lon, p.snap_lat],
              ],
            },
            properties: { name: p.name },
          });
        }
      }
    });

    const geojson = {
      type: 'FeatureCollection',
      features: snapLineFeatures,
    };

    if (m.getSource(sourceId)) {
      m.getSource(sourceId).setData(geojson);
    } else if (snapLineFeatures.length > 0) {
      m.addSource(sourceId, { type: 'geojson', data: geojson });
      m.addLayer({
        id: layerId,
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': '#e040fb',
          'line-width': 2.5,
          'line-dasharray': [3, 3],
          'line-opacity': 0.9,
        },
        layout: {
          'line-cap': 'round',
          'line-join': 'round',
        },
      });
    }
  }, [mapReady, startNode, destinations, pois]);

  // ── 2. Persistent Shortest & Fastest Route lines effect ─────────────
  useEffect(() => {
    if (!mapReady || !map.current) return;
    const m = map.current;

    if (!searchResult) {
      ['shortest-route', 'fastest-route'].forEach((id) => {
        if (m.getLayer(`${id}-arrows`)) m.removeLayer(`${id}-arrows`);
        if (m.getLayer(`${id}-layer`)) m.removeLayer(`${id}-layer`);
        if (m.getSource(id)) m.removeSource(id);
      });
      return;
    }

    // Determine active route coordinates for Shortest route
    let activeShortestCoords = [];
    if (animState && animState.completedLegsCoords !== null) {
      animState.completedLegsCoords.forEach((legCoords) => {
        if (!legCoords || legCoords.length === 0) return;
        if (activeShortestCoords.length === 0) {
          activeShortestCoords.push(...legCoords);
        } else {
          activeShortestCoords.push(...legCoords.slice(1));
        }
      });
    } else {
      activeShortestCoords = searchResult.shortest_result?.path_coords || [];
    }

    const fastestCoords = searchResult.fastest_result?.path_coords || [];

    // ── Shortest Route Layer ──
    const shortestGeojson = {
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: activeShortestCoords.length >= 2 ? activeShortestCoords : [],
      },
    };

    if (m.getSource('shortest-route')) {
      m.getSource('shortest-route').setData(shortestGeojson);
    } else if (activeShortestCoords.length >= 2) {
      m.addSource('shortest-route', { type: 'geojson', data: shortestGeojson });
      m.addLayer({
        id: 'shortest-route-layer',
        type: 'line',
        source: 'shortest-route',
        paint: {
          'line-color': '#4a90d9',
          'line-width': 5,
          'line-opacity': 0.9,
        },
        layout: {
          'line-cap': 'round',
          'line-join': 'round',
        },
      });
      m.addLayer({
        id: 'shortest-route-arrows',
        type: 'symbol',
        source: 'shortest-route',
        layout: {
          'symbol-placement': 'line',
          'symbol-spacing': 60,
          'icon-image': 'arrow-blue',
          'icon-size': 0.65,
          'icon-allow-overlap': true,
          'icon-ignore-placement': true,
          'icon-keep-upright': false,
          'icon-rotation-alignment': 'line',
        },
      });
    }

    // ── Fastest Route Layer ──
    const showFastest = fastestCoords.length >= 2 && (!animState || !animState.isAnimating);
    const fastestGeojson = {
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: showFastest ? fastestCoords : [],
      },
    };

    if (m.getSource('fastest-route')) {
      m.getSource('fastest-route').setData(fastestGeojson);
    } else if (showFastest) {
      m.addSource('fastest-route', { type: 'geojson', data: fastestGeojson });
      m.addLayer({
        id: 'fastest-route-layer',
        type: 'line',
        source: 'fastest-route',
        paint: {
          'line-color': '#ff6b6b',
          'line-width': 5,
          'line-opacity': 0.8,
        },
        layout: {
          'line-cap': 'round',
          'line-join': 'round',
        },
      });
      m.addLayer({
        id: 'fastest-route-arrows',
        type: 'symbol',
        source: 'fastest-route',
        layout: {
          'symbol-placement': 'line',
          'symbol-spacing': 60,
          'icon-image': 'arrow-red',
          'icon-size': 0.65,
          'icon-allow-overlap': true,
          'icon-ignore-placement': true,
          'icon-keep-upright': false,
          'icon-rotation-alignment': 'line',
        },
      });
    }

    // Fit map bounds on initial search result arrival
    if (!animState || !animState.isAnimating) {
      const allCoords = [...(searchResult.shortest_result?.path_coords || []), ...fastestCoords];
      if (allCoords.length > 0) {
        const bounds = allCoords.reduce(
          (b, c) => b.extend(c),
          new maplibregl.LngLatBounds(allCoords[0], allCoords[0])
        );
        m.fitBounds(bounds, { padding: 60, duration: 1000 });
      }
    }
  }, [mapReady, searchResult, animState?.completedLegsCoords, animState?.isAnimating]);

  // ── 3. Draw search process animation (Gray Edges + Nodes) ───────────
  useEffect(() => {
    if (!mapReady || !map.current) return;
    const m = map.current;

    const edgeSourceId = 'explored-edges';
    const edgeLayerId = 'explored-edges-layer';
    const pointSourceId = 'explored-points';
    const pointLayerId = 'explored-points-layer';

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
        return {
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: coords,
          },
        };
      })
      .filter(Boolean);

    const edgeGeojson = {
      type: 'FeatureCollection',
      features: edgeFeatures,
    };

    if (m.getSource(edgeSourceId)) {
      m.getSource(edgeSourceId).setData(edgeGeojson);
    } else if (edgeFeatures.length > 0) {
      m.addSource(edgeSourceId, { type: 'geojson', data: edgeGeojson });
      m.addLayer({
        id: edgeLayerId,
        type: 'line',
        source: edgeSourceId,
        paint: {
          'line-color': '#777777', // Gray search tree edge
          'line-width': 2.5,
          'line-opacity': 0.75,
        },
        layout: {
          'line-cap': 'round',
          'line-join': 'round',
        },
      });
    }

    // ── Explored Nodes (Circles) ──
    const nodeFeatures = activeNodes
      .map((nodeId, i) => {
        const coords = nodeCoordsMap.get(nodeId);
        if (!coords) return null;
        return {
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: coords,
          },
          properties: { order: i },
        };
      })
      .filter(Boolean);

    const nodeGeojson = {
      type: 'FeatureCollection',
      features: nodeFeatures,
    };

    if (m.getSource(pointSourceId)) {
      m.getSource(pointSourceId).setData(nodeGeojson);
    } else if (nodeFeatures.length > 0) {
      m.addSource(pointSourceId, { type: 'geojson', data: nodeGeojson });
      m.addLayer({
        id: pointLayerId,
        type: 'circle',
        source: pointSourceId,
        paint: {
          'circle-radius': 3,
          'circle-color': [
            'interpolate',
            ['linear'],
            ['get', 'order'],
            0, '#51cf66',
            Math.max(1, nodeFeatures.length * 0.5), '#fcc419',
            Math.max(2, nodeFeatures.length), '#ff6b6b',
          ],
          'circle-opacity': 0.7,
        },
      });
    }
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
          <div className="map-legend__item">
            <span className="map-legend__line map-legend__line--shortest" />
            <span>Shortest route</span>
          </div>
          <div className="map-legend__item">
            <span className="map-legend__line map-legend__line--fastest" />
            <span>Fastest route</span>
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
}
