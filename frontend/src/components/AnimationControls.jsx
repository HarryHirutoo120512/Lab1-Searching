import { useState, useRef, useEffect, useMemo } from 'react';

export default function AnimationControls({
  legs,
  onAnimUpdate,
  onTakeScreenshot,
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

  const handlePrevStep = () => {
    if (isPlaying) handlePause();
    if (currentIndex.current > 0) {
      currentIndex.current--;
      setProgress(currentIndex.current / totalSteps);
      emitStep(currentIndex.current);
    }
  };

  const handleNextStep = () => {
    if (isPlaying) handlePause();
    if (currentIndex.current < totalSteps) {
      currentIndex.current++;
      setProgress(currentIndex.current / totalSteps);
      emitStep(currentIndex.current);
    }
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
        title={isPlaying ? 'Pause (Tạm dừng)' : 'Play (Phát)'}
      >
        {isPlaying ? (
          <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" style={{ marginLeft: '2px' }}>
            <path d="M8 5v14l11-7z" />
          </svg>
        )}
      </button>

      {/* Previous Step */}
      <button
        className="animation-controls__btn"
        onClick={handlePrevStep}
        disabled={currentIndex.current <= 0}
        title="Previous step (Bước trước)"
        style={{ background: '#4a90d9' }}
      >
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
          <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z" />
        </svg>
      </button>

      {/* Next Step */}
      <button
        className="animation-controls__btn"
        onClick={handleNextStep}
        disabled={currentIndex.current >= totalSteps}
        title="Next step (Bước tiếp)"
        style={{ background: '#4a90d9' }}
      >
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
          <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z" />
        </svg>
      </button>

      {/* Reset */}
      <button
        className="animation-controls__btn"
        onClick={handleReset}
        title="Reset (Đặt lại)"
        style={{ background: '#6c757d' }}
      >
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
          <path d="M3 3v5h5" />
        </svg>
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
        title={`Speed: ${speed}x (Tốc độ)`}
        style={{ background: '#845ef7', fontSize: '11px', fontWeight: 700 }}
      >
        {speed}x
      </button>

      {/* Screenshot */}
      <button
        className="animation-controls__btn"
        onClick={onTakeScreenshot}
        title="Take screenshot (Chụp ảnh bản đồ)"
        style={{ background: '#10b981' }}
      >
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
          <circle cx="12" cy="13" r="4" />
        </svg>
      </button>
    </div>
  );
}
