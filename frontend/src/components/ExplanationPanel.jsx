import { useState } from 'react';

const ICON_MAP = {
  'start': '🚩',
  'straight': '⬆️',
  'turn-right': '↗️',
  'turn-left': '↖️',
  'u-turn': '↩️',
  'arrive': '📍',
};

export default function ExplanationPanel({
  explanation,
  algorithmInfo,
  shortestDirections,
  fastestDirections,
  routeMode = 'shortest',
  setRouteMode,
}) {
  if (!explanation) return null;

  // Convert markdown-like bold (**text**) to <strong>
  const renderFormattedText = (text) => {
    if (!text) return null;
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  const activeTab = routeMode;
  const handleTabChange = (mode) => {
    if (setRouteMode) setRouteMode(mode);
  };

  const activeDirections = activeTab === 'shortest' ? shortestDirections : fastestDirections;

  return (
    <div className="explanation-panel">
      <h3 className="explanation-panel__title">
        💡 Route Explanation
      </h3>

      {algorithmInfo && (
        <div style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '12px',
          flexWrap: 'wrap',
        }}>
          <span className="stats-badge" style={{
            background: 'rgba(132, 94, 247, 0.1)',
            color: '#7048e8',
          }}>
            {algorithmInfo.name}
          </span>
          <span className={`stats-badge ${
            algorithmInfo.optimal ? 'stats-badge--winner' : 'stats-badge--loser'
          }`}>
            {algorithmInfo.optimal ? '✓ Optimal' : '~ Approximate'}
          </span>
          <span className={`stats-badge ${
            algorithmInfo.complete ? 'stats-badge--winner' : 'stats-badge--loser'
          }`}>
            {algorithmInfo.complete ? '✓ Complete' : '✗ Incomplete'}
          </span>
        </div>
      )}

      <div className="explanation-panel__content">
        {renderFormattedText(explanation)}
      </div>

      {/* Turn-by-turn Navigation Directions */}
      {(shortestDirections?.length > 0 || fastestDirections?.length > 0) && (
        <div className="directions-container">
          <div className="directions-title">
            🧭 Turn-by-Turn Navigation ({activeTab === 'shortest' ? 'Shortest' : 'Fastest'})
          </div>

          <div className="directions-tabs">
            <button
              className={`directions-tab directions-tab--shortest ${activeTab === 'shortest' ? 'active' : ''}`}
              onClick={() => handleTabChange('shortest')}
            >
              🔵 Shortest Route ({shortestDirections?.length || 0} steps)
            </button>
            <button
              className={`directions-tab directions-tab--fastest ${activeTab === 'fastest' ? 'active' : ''}`}
              onClick={() => handleTabChange('fastest')}
            >
              🔴 Fastest Route ({fastestDirections?.length || 0} steps)
            </button>
          </div>

          <div className="directions-list">
            {activeDirections && activeDirections.map((step, idx) => (
              <div
                key={idx}
                className={`directions-item ${
                  step.icon === 'start'
                    ? 'directions-item--start'
                    : step.icon === 'arrive'
                    ? 'directions-item--arrive'
                    : ''
                }`}
              >
                <span className="directions-item__icon">
                  {ICON_MAP[step.icon] || '➡️'}
                </span>
                <span style={{ flex: 1 }}>
                  {renderFormattedText(step.text)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
