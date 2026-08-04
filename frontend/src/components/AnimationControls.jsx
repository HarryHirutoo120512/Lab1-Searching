import { useState, useRef, useEffect, useMemo } from 'react';

export default function AnimationControls({
  legs,
  onAnimUpdate,
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [speed, setSpeed] = useState(1);
  const currentIndex = useRef(0);
  const timerRef = useRef(null);

  // Flatten all explored steps across legs and compute leg boundaries
  const { flatSteps, legBoundaries, totalSteps } = useMemo(() => {
    if (!legs || legs.length === 0) {
      return { flatSteps: [], legBoundaries: [], totalSteps: 0 };
    }
    const flat = [];
    const boundaries = [];

    legs.forEach((leg, legIdx) => {
      const steps = leg.explored || [];
      steps.forEach((step) => {
        flat.push({
          node: step.node,
          parent: step.parent,
          legIndex: legIdx,
        });
      });
      boundaries.push(flat.length);
    });

    return {
      flatSteps: flat,
      legBoundaries: boundaries,
      totalSteps: flat.length,
    };
  }, [legs]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  useEffect(() => {
    // Reset state when new search results arrive
    currentIndex.current = 0;
    setProgress(0);
    setIsPlaying(false);
    if (timerRef.current) clearTimeout(timerRef.current);
    if (onAnimUpdate) {
      onAnimUpdate({
        completedLegsCoords: null, // null means show default full route when not animating
        activeExploredEdges: [],
        activeExploredNodes: [],
        isAnimating: false,
      });
    }
  }, [legs]);

  const emitStep = (idx) => {
    if (!legs || legs.length === 0) return;

    if (idx === 0) {
      onAnimUpdate({
        completedLegsCoords: [],
        activeExploredEdges: [],
        activeExploredNodes: [],
        isAnimating: true,
      });
      return;
    }

    // Determine current leg index for step idx
    let currentLegIdx = 0;
    for (let i = 0; i < legBoundaries.length; i++) {
      if (idx > (i === 0 ? 0 : legBoundaries[i - 1])) {
        currentLegIdx = i;
      }
    }

    // A leg is considered completed if the animation index has reached or passed its boundary
    const completedLegsCount = legBoundaries.filter((b) => idx >= b).length;
    const completedLegsCoords = legs
      .slice(0, completedLegsCount)
      .map((l) => l.path_coords)
      .filter(Boolean);

    // Only show the CURRENT leg's explored search tree (clear previous legs' gray edges)
    const legStartIdx = currentLegIdx === 0 ? 0 : legBoundaries[currentLegIdx - 1];
    const activeSteps = flatSteps.slice(legStartIdx, idx);

    const activeExploredEdges = activeSteps
      .filter((s) => s.parent !== null && s.parent !== undefined)
      .map((s) => ({ parent: s.parent, node: s.node }));

    const activeExploredNodes = activeSteps.map((s) => s.node);

    onAnimUpdate({
      completedLegsCoords,
      activeExploredEdges,
      activeExploredNodes,
      isAnimating: true,
    });
  };

  const tick = () => {
    if (currentIndex.current >= totalSteps) {
      setIsPlaying(false);
      emitStep(totalSteps);
      return;
    }

    currentIndex.current++;
    setProgress(currentIndex.current / totalSteps);
    emitStep(currentIndex.current);

    // Check if we hit a leg boundary for intermediate pausing
    const isAtLegBoundary = legBoundaries.includes(currentIndex.current);
    if (isAtLegBoundary && currentIndex.current < totalSteps) {
      // Pause animation at end of current leg so user must click Play to continue to next leg
      setIsPlaying(false);
      return;
    }

    const interval = Math.max(4, 30 / speed);
    timerRef.current = setTimeout(tick, interval);
  };

  const handlePlay = () => {
    if (currentIndex.current >= totalSteps) {
      currentIndex.current = 0;
      setProgress(0);
    }
    setIsPlaying(true);
    tick();
  };

  const handlePause = () => {
    setIsPlaying(false);
    if (timerRef.current) clearTimeout(timerRef.current);
  };

  const handleReset = () => {
    handlePause();
    currentIndex.current = 0;
    setProgress(0);
    if (onAnimUpdate) {
      onAnimUpdate({
        completedLegsCoords: null, // null = show default full route
        activeExploredEdges: [],
        activeExploredNodes: [],
        isAnimating: false,
      });
    }
  };

  const cycleSpeed = () => {
    const speeds = [0.5, 1, 2, 5, 10];
    const idx = speeds.indexOf(speed);
    setSpeed(speeds[(idx + 1) % speeds.length]);
  };

  if (!legs || totalSteps === 0) return null;

  return (
    <div className="animation-controls">
      {/* Play/Pause */}
      <button
        className="animation-controls__btn"
        onClick={isPlaying ? handlePause : handlePlay}
        title={isPlaying ? 'Pause' : 'Play'}
      >
        {isPlaying ? '⏸' : '▶'}
      </button>

      {/* Reset */}
      <button
        className="animation-controls__btn"
        onClick={handleReset}
        title="Reset"
        style={{ background: '#6c757d' }}
      >
        ↺
      </button>

      {/* Progress bar */}
      <div className="animation-controls__progress">
        <div
          className="animation-controls__progress-bar"
          style={{ width: `${progress * 100}%` }}
        />
      </div>

      {/* Step counter */}
      <span className="animation-controls__speed" style={{ minWidth: '60px', textAlign: 'center' }}>
        {currentIndex.current} / {totalSteps}
      </span>

      {/* Speed */}
      <button
        className="animation-controls__btn"
        onClick={cycleSpeed}
        title={`Speed: ${speed}x`}
        style={{ background: '#845ef7', fontSize: '11px', fontWeight: 700 }}
      >
        {speed}x
      </button>
    </div>
  );
}
