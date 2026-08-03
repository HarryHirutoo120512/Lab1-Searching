/**
 * Exploration animation engine.
 * Replays the sequence of explored nodes from the backend,
 * calling onStep(node, frontier, index) for each step.
 */
export class AnimationEngine {
  constructor(exploredSteps, onStep, onComplete) {
    this.steps = exploredSteps || [];
    this.onStep = onStep;
    this.onComplete = onComplete;
    this.currentIndex = 0;
    this.isPlaying = false;
    this.speed = 1; // multiplier
    this.baseInterval = 30; // ms per step
    this._timer = null;
  }

  get totalSteps() {
    return this.steps.length;
  }

  get progress() {
    if (this.totalSteps === 0) return 0;
    return this.currentIndex / this.totalSteps;
  }

  play() {
    if (this.isPlaying) return;
    this.isPlaying = true;
    this._tick();
  }

  pause() {
    this.isPlaying = false;
    if (this._timer) {
      clearTimeout(this._timer);
      this._timer = null;
    }
  }

  reset() {
    this.pause();
    this.currentIndex = 0;
  }

  setSpeed(multiplier) {
    this.speed = multiplier;
  }

  _tick() {
    if (!this.isPlaying) return;
    if (this.currentIndex >= this.totalSteps) {
      this.isPlaying = false;
      if (this.onComplete) this.onComplete();
      return;
    }

    const step = this.steps[this.currentIndex];
    this.onStep(step, this.currentIndex);
    this.currentIndex++;

    const interval = Math.max(5, this.baseInterval / this.speed);
    this._timer = setTimeout(() => this._tick(), interval);
  }

  destroy() {
    this.pause();
    this.steps = [];
  }
}
