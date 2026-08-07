export default function StatsPanel({ shortestStats, fastestStats, routeMode = 'shortest', setRouteMode }) {
  if (!shortestStats || !fastestStats) return null;

  const formatDist = (m) =>
    m >= 1000 ? `${(m / 1000).toFixed(2)} km` : `${m.toFixed(0)} m`;

  const formatTime = (s) => {
    if (s < 60) return `${s.toFixed(0)}s`;
    const min = Math.floor(s / 60);
    const sec = Math.round(s % 60);
    return `${min}m ${sec}s`;
  };

  const rows = [
    {
      label: 'Distance',
      sVal: formatDist(shortestStats.total_distance),
      fVal: formatDist(fastestStats.total_distance),
      sRaw: shortestStats.total_distance,
      fRaw: fastestStats.total_distance,
      lowerBetter: true,
    },
    {
      label: 'Travel Time',
      sVal: formatTime(shortestStats.total_time),
      fVal: formatTime(fastestStats.total_time),
      sRaw: shortestStats.total_time,
      fRaw: fastestStats.total_time,
      lowerBetter: true,
    },
    {
      label: 'Congestion',
      sVal: formatTime(shortestStats.total_congestion),
      fVal: formatTime(fastestStats.total_congestion),
      sRaw: shortestStats.total_congestion,
      fRaw: fastestStats.total_congestion,
      lowerBetter: true,
    },
    {
      label: 'Risk Score',
      sVal: shortestStats.total_risk.toFixed(2),
      fVal: fastestStats.total_risk.toFixed(2),
      sRaw: shortestStats.total_risk,
      fRaw: fastestStats.total_risk,
      lowerBetter: true,
    },
    {
      label: 'Total Cost',
      sVal: shortestStats.total_cost.toFixed(4),
      fVal: fastestStats.total_cost.toFixed(4),
      sRaw: shortestStats.total_cost,
      fRaw: fastestStats.total_cost,
      lowerBetter: true,
    },
    {
      label: 'Expanded Nodes',
      sVal: shortestStats.expanded_nodes.toLocaleString(),
      fVal: fastestStats.expanded_nodes.toLocaleString(),
      sRaw: shortestStats.expanded_nodes,
      fRaw: fastestStats.expanded_nodes,
      lowerBetter: true,
    },
    {
      label: 'Exec Time',
      sVal: `${shortestStats.execution_time.toFixed(1)} ms`,
      fVal: `${fastestStats.execution_time.toFixed(1)} ms`,
      sRaw: shortestStats.execution_time,
      fRaw: fastestStats.execution_time,
      lowerBetter: true,
    },
  ];

  return (
    <div className="stats-panel">
      <h3 className="stats-panel__title">
        📊 Route Comparison
      </h3>
      <table className="stats-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th
              className={`stats-col--shortest ${routeMode === 'shortest' ? 'stats-col--active' : ''}`}
              style={{ cursor: 'pointer', background: routeMode === 'shortest' ? 'rgba(74, 144, 217, 0.15)' : 'transparent', borderRadius: '4px' }}
              onClick={() => setRouteMode && setRouteMode('shortest')}
              title="Click to select Shortest route"
            >
              🔵 Shortest {routeMode === 'shortest' ? '✓' : ''}
            </th>
            <th
              className={`stats-col--fastest ${routeMode === 'fastest' ? 'stats-col--active' : ''}`}
              style={{ cursor: 'pointer', background: routeMode === 'fastest' ? 'rgba(255, 107, 107, 0.15)' : 'transparent', borderRadius: '4px' }}
              onClick={() => setRouteMode && setRouteMode('fastest')}
              title="Click to select Fastest route"
            >
              🔴 Fastest {routeMode === 'fastest' ? '✓' : ''}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const sWins = row.lowerBetter
              ? row.sRaw <= row.fRaw
              : row.sRaw >= row.fRaw;
            const fWins = !sWins;
            const tie = Math.abs(row.sRaw - row.fRaw) < 0.0001;

            return (
              <tr key={row.label}>
                <td style={{ fontWeight: 500 }}>{row.label}</td>
                <td>
                  <span className={`stats-badge ${tie ? '' : sWins ? 'stats-badge--winner' : 'stats-badge--loser'}`}>
                    {!tie && sWins && '✓ '}
                    {row.sVal}
                  </span>
                </td>
                <td>
                  <span className={`stats-badge ${tie ? '' : fWins ? 'stats-badge--winner' : 'stats-badge--loser'}`}>
                    {!tie && fWins && '✓ '}
                    {row.fVal}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
