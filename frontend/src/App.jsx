import { useState, useEffect, useCallback } from 'react';
import MapView from './components/MapView';
import ControlPanel from './components/ControlPanel';
import StatsPanel from './components/StatsPanel';
import ExplanationPanel from './components/ExplanationPanel';
import AnimationControls from './components/AnimationControls';
import { fetchLocations, fetchNetwork, searchRoutes } from './utils/api';

export default function App() {
  // ── State ───────────────────────────────────────────────────────────
  const [pois, setPois] = useState([]);
  const [network, setNetwork] = useState(null);
  const [algorithm, setAlgorithm] = useState('astar');
  const [startNode, setStartNode] = useState(null);
  const [destinations, setDestinations] = useState([null]);
  const [searchResult, setSearchResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState({ text: 'Loading map data…', type: 'info' });
  const [exploredNodes, setExploredNodes] = useState([]);
  const [showDebug, setShowDebug] = useState(false);

  // ── Load initial data ───────────────────────────────────────────────
  useEffect(() => {
    const loadData = async () => {
      try {
        const [locData, netData] = await Promise.all([
          fetchLocations(),
          fetchNetwork(),
        ]);
        setPois(locData.pois || []);
        setNetwork(netData);
        setStatus({
          text: `Loaded ${locData.pois?.length || 0} POIs · ${locData.total_nodes || 0} nodes`,
          type: 'info',
        });
      } catch (err) {
        setStatus({ text: `Failed to load data: ${err.message}`, type: 'error' });
      }
    };
    loadData();
  }, []);

  // ── Handlers ────────────────────────────────────────────────────────
  const handleSearch = useCallback(async () => {
    const validDests = destinations.filter((d) => d !== null);
    if (!startNode || validDests.length === 0) return;

    setIsLoading(true);
    setSearchResult(null);
    setExploredNodes([]);
    setStatus({ text: 'Searching routes…', type: 'info' });

    try {
      const result = await searchRoutes({
        algorithm,
        startNode,
        destinations: validDests,
      });
      setSearchResult(result);
      setStatus({
        text: `Search complete — ${result.algorithm_info?.name || algorithm}`,
        type: 'info',
      });
    } catch (err) {
      setStatus({ text: `Search failed: ${err.message}`, type: 'error' });
    } finally {
      setIsLoading(false);
    }
  }, [algorithm, startNode, destinations]);

  const handleReset = useCallback(() => {
    setSearchResult(null);
    setExploredNodes([]);
    setStartNode(null);
    setDestinations([null]);
    setStatus({ text: 'Ready', type: 'info' });
  }, []);

  const handleMapClick = useCallback(
    ({ lat, lon }) => {
      // Find nearest POI to click
      if (pois.length === 0) return;
      let nearest = pois[0];
      let bestDist = Infinity;
      for (const p of pois) {
        const d = Math.sqrt((p.lat - lat) ** 2 + (p.lon - lon) ** 2);
        if (d < bestDist) {
          bestDist = d;
          nearest = p;
        }
      }
      // Auto-fill the first empty field
      if (startNode === null) {
        setStartNode(nearest.id);
      } else {
        const emptyIdx = destinations.findIndex((d) => d === null);
        if (emptyIdx >= 0) {
          const updated = [...destinations];
          updated[emptyIdx] = nearest.id;
          setDestinations(updated);
        }
      }
    },
    [pois, startNode, destinations]
  );

  // Get explored steps for animation (use shortest result)
  const exploredSteps = searchResult?.shortest_result?.explored || [];

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div className="app">
      {/* Sidebar */}
      <div className="app__sidebar">
        <ControlPanel
          pois={pois}
          algorithm={algorithm}
          setAlgorithm={setAlgorithm}
          startNode={startNode}
          setStartNode={setStartNode}
          destinations={destinations}
          setDestinations={setDestinations}
          onSearch={handleSearch}
          onReset={handleReset}
          isLoading={isLoading}
          showDebug={showDebug}
          setShowDebug={setShowDebug}
        />

        {/* Stats */}
        {searchResult && (
          <StatsPanel
            shortestStats={searchResult.shortest_result?.stats}
            fastestStats={searchResult.fastest_result?.stats}
          />
        )}

        {/* Explanation & Directions */}
        {searchResult && (
          <ExplanationPanel
            explanation={searchResult.explanation}
            algorithmInfo={searchResult.algorithm_info}
            shortestDirections={searchResult.shortest_result?.directions}
            fastestDirections={searchResult.fastest_result?.directions}
          />
        )}

        {/* Status bar */}
        <div style={{ marginTop: 'auto' }}>
          <div className={`status-bar ${status.type === 'error' ? 'status-bar--error' : ''}`}>
            <span className="status-bar__icon">
              {status.type === 'error' ? '⚠️' : isLoading ? '⏳' : '✨'}
            </span>
            {status.text}
          </div>
        </div>
      </div>

      {/* Map */}
      <MapView
        network={network}
        searchResult={searchResult}
        startNode={startNode}
        destinations={destinations}
        pois={pois}
        onMapClick={handleMapClick}
        exploredNodes={exploredNodes}
        showDebug={showDebug}
      />

      {/* Animation controls (floating on map) */}
      {searchResult && (
        <AnimationControls
          exploredSteps={exploredSteps}
          onExploredNodesUpdate={setExploredNodes}
        />
      )}
    </div>
  );
}
