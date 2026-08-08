import { useState, useEffect, useCallback, useRef } from 'react';
import MapView from './components/MapView';
import ControlPanel from './components/ControlPanel';
import StatsPanel from './components/StatsPanel';
import ExplanationPanel from './components/ExplanationPanel';
import AnimationControls from './components/AnimationControls';
import { fetchLocations, fetchNetwork, searchRoutes } from './utils/api';

export default function App() {
  // ── State & Refs ───────────────────────────────────────────────────
  const mapViewRef = useRef(null);
  const [pois, setPois] = useState([]);
  const [network, setNetwork] = useState(null);
  const [algorithm, setAlgorithm] = useState('astar');
  const [startNode, setStartNode] = useState(null);
  const [destinations, setDestinations] = useState([null]);
  const [searchResult, setSearchResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState({ text: 'Loading map data…', type: 'info' });
  const [animState, setAnimState] = useState(null);
  const [showDebug, setShowDebug] = useState(false);
  const [routeMode, setRouteMode] = useState('shortest'); // default 'shortest'

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

  // Reset search results whenever startNode or destinations change
  useEffect(() => {
    setSearchResult(null);
    setAnimState(null);
  }, [startNode, destinations]);

  // ── Handlers ────────────────────────────────────────────────────────
  const handleSearch = useCallback(async () => {
    const validDests = destinations.filter((d) => d !== null);
    if (!startNode || validDests.length === 0) return;

    setIsLoading(true);
    setSearchResult(null);
    setAnimState(null);
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
    setAnimState(null);
    setStartNode(null);
    setDestinations([null]);
    setStatus({ text: 'Ready', type: 'info' });
  }, []);

  const handleTakeScreenshot = useCallback(() => {
    if (mapViewRef.current && mapViewRef.current.takeScreenshot) {
      mapViewRef.current.takeScreenshot();
    }
  }, []);

  // Legs array for animation based on selected route mode
  const legs =
    routeMode === 'fastest'
      ? searchResult?.legs_fastest || []
      : searchResult?.legs_shortest || [];

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div className="app">
      {/* Sidebar */}
      <div className="app__sidebar">
        <ControlPanel
          pois={pois}
          algorithm={algorithm}
          setAlgorithm={setAlgorithm}
          routeMode={routeMode}
          setRouteMode={setRouteMode}
          startNode={startNode}
          setStartNode={setStartNode}
          destinations={destinations}
          setDestinations={setDestinations}
          onSearch={handleSearch}
          onReset={handleReset}
          isLoading={isLoading}
          showDebug={showDebug}
          setShowDebug={setShowDebug}
          searchResult={searchResult}
        />

        {/* Stats */}
        {searchResult && (
          <StatsPanel
            shortestStats={searchResult.shortest_result?.stats}
            fastestStats={searchResult.fastest_result?.stats}
            routeMode={routeMode}
            setRouteMode={setRouteMode}
          />
        )}

        {/* Explanation & Directions */}
        {searchResult && (
          <ExplanationPanel
            explanation={searchResult.explanation}
            algorithmInfo={searchResult.algorithm_info}
            shortestDirections={searchResult.shortest_result?.directions}
            fastestDirections={searchResult.fastest_result?.directions}
            routeMode={routeMode}
            setRouteMode={setRouteMode}
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
        ref={mapViewRef}
        network={network}
        searchResult={searchResult}
        routeMode={routeMode}
        startNode={startNode}
        destinations={destinations}
        pois={pois}
        animState={animState}
        showDebug={showDebug}
      />

      {/* Animation controls (floating on map) */}
      {searchResult && (
        <AnimationControls
          legs={legs}
          onAnimUpdate={setAnimState}
          onTakeScreenshot={handleTakeScreenshot}
        />
      )}
    </div>
  );
}
