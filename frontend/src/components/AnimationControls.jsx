import { useState, useRef, useEffect } from 'react';

export default function AnimationControls({
  exploredSteps,
  onExploredNodesUpdate,
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [speed, setSpeed] = useState(1);
  const currentIndex = useRef(0);
  const timerRef = useRef(null);
  const exploredRef = useRef([]);

  const totalSteps = exploredSteps?.length || 0;

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  useEffect(() => {
    // Reset when new data arrives
    currentIndex.current = 0;
    exploredRef.current = [];
    setProgress(0);
    setIsPlaying(false);
    if (timerRef.current) clearTimeout(timerRef.current);
  }, [exploredSteps]);

  const tick = () => {
    if (currentIndex.current >= totalSteps) {
      setIsPlaying(false);
      return;
    }

    const step = exploredSteps[currentIndex.current];
    exploredRef.current.push(step.node);
    currentIndex.current++;
    setProgress(currentIndex.current / totalSteps);
    onExploredNodesUpdate([...exploredRef.current]);

    const interval = Math.max(5, 30 / speed);
    timerRef.current = setTimeout(tick, interval);
  };

  const handlePlay = () => {
    if (currentIndex.current >= totalSteps) {
      // Reset and replay
      currentIndex.current = 0;
      exploredRef.current = [];
      onExploredNodesUpdate([]);
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
    exploredRef.current = [];
    setProgress(0);
    onExploredNodesUpdate([]);
  };

  const cycleSpeed = () => {
    const speeds = [0.5, 1, 2, 5, 10];
    const idx = speeds.indexOf(speed);
    setSpeed(speeds[(idx + 1) % speeds.length]);
  };

  if (!exploredSteps || totalSteps === 0) return null;

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
