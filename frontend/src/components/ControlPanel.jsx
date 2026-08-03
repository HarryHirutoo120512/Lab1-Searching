import { useState } from 'react';

const ALGORITHMS = [
  { value: 'astar', label: 'A* Search' },
  { value: 'ucs', label: 'Uniform Cost Search' },
  { value: 'bfs', label: 'Breadth-First Search' },
  { value: 'dfs', label: 'Depth-First Search' },
  { value: 'gbfs', label: 'Greedy Best-First Search' },
  { value: 'bidirectional', label: 'Bidirectional BFS' },
];

export default function ControlPanel({
  pois,
  algorithm,
  setAlgorithm,
  startNode,
  setStartNode,
  destinations,
  setDestinations,
  onSearch,
  onReset,
  isLoading,
  showDebug,
  setShowDebug,
}) {
  const handleAddDestination = () => {
    setDestinations([...destinations, null]);
  };

  const handleRemoveDestination = (index) => {
    setDestinations(destinations.filter((_, i) => i !== index));
  };

  const handleDestinationChange = (index, value) => {
    const updated = [...destinations];
    updated[index] = value ? parseInt(value) : null;
    setDestinations(updated);
  };

  const canSearch =
    startNode !== null &&
    destinations.length > 0 &&
    destinations.every((d) => d !== null);

  return (
    <>
      {/* Header */}
      <div className="header">
        <h1 className="header__title">
          <span className="header__title-icon">🗺️</span>
          Route Planner
        </h1>
        <p className="header__subtitle">
          District 1, Ho Chi Minh City — AI Search Visualization
        </p>
      </div>

      <div className="control-panel">
        {/* Algorithm selector */}
        <div className="control-panel__section">
          <label className="control-panel__label">Algorithm</label>
          <select
            className="control-panel__select"
            value={algorithm}
            onChange={(e) => setAlgorithm(e.target.value)}
          >
            {ALGORITHMS.map((a) => (
              <option key={a.value} value={a.value}>
                {a.label}
              </option>
            ))}
          </select>
        </div>

        {/* Start location */}
        <div className="control-panel__section">
          <label className="control-panel__label">Start Location</label>
          <div className="location-row">
            <div className="location-row__marker location-row__marker--start">S</div>
            <select
              className="control-panel__select"
              value={startNode || ''}
              onChange={(e) => setStartNode(e.target.value ? parseInt(e.target.value) : null)}
            >
              <option value="">Select start point…</option>
              {pois.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Destinations */}
        <div className="control-panel__section">
          <label className="control-panel__label">Destinations</label>
          {destinations.map((dest, index) => (
            <div className="location-row" key={index} style={{ animation: 'slideIn 0.3s ease' }}>
              <div
                className={`location-row__marker ${
                  destinations.length === 1
                    ? 'location-row__marker--end'
                    : 'location-row__marker--multi'
                }`}
              >
                {destinations.length === 1 ? 'D' : index + 1}
              </div>
              <select
                className="control-panel__select"
                value={dest || ''}
                onChange={(e) => handleDestinationChange(index, e.target.value)}
              >
                <option value="">Select destination…</option>
                {pois
                  .filter(
                    (p) =>
                      p.id !== startNode &&
                      !destinations.some((d, i) => i !== index && d === p.id)
                  )
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
              </select>
              <button
                className="location-row__remove"
                onClick={() => handleRemoveDestination(index)}
                title="Remove destination"
              >
                ×
              </button>
            </div>
          ))}

          <button className="add-destination-btn" onClick={handleAddDestination}>
            + Add destination
          </button>
        </div>

        {/* Action buttons */}
        <div className="btn-group">
          <button
            className={`btn btn--primary btn--full ${isLoading ? 'btn--loading' : ''}`}
            onClick={onSearch}
            disabled={!canSearch || isLoading}
          >
            {isLoading ? (
              <>
                <span className="btn__spinner" />
                Searching…
              </>
            ) : (
              <>🔍 Search Routes</>
            )}
          </button>
          <button className="btn btn--secondary" onClick={onReset}>
            Reset
          </button>
        </div>

        {/* Debug overlay toggle */}
        <label className="debug-toggle">
          <input
            type="checkbox"
            checked={showDebug}
            onChange={(e) => setShowDebug(e.target.checked)}
            className="debug-toggle__checkbox"
          />
          <span className="debug-toggle__label">🐛 Show Network Debug Overlay</span>
        </label>
      </div>
    </>
  );
}
