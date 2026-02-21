// GenieGuard: World-Sim CI - Telemetry System (v3 — Tier 2 extended)
// Exposes simulation data via window.__telemetry__

import { SIM_CONFIG } from './config.js';

class TelemetrySystem {
  constructor() {
    this.startTime = Date.now();
    this.frameCount = 0;
    this.collisionCount = 0;
    this.ballData = { x: 0, y: 0, vx: 0, vy: 0, mass: 0, radius: 0, angle: 0, angularVelocity: 0, inertia: 0 };
    this.errors = [];
    this.history = [];
    this.maxHistory = 100;

    // Ready flag — true after first update() with valid ball data
    this.ready = false;

    // Ball exists flag — true when update() receives a valid ball
    this.ballExists = false;

    // Frame timing
    this.lastUpdateTime = null;
    this.frameDelta = 0;

    // Previous frame data
    this.prevBallData = null;

    // Peak tracking
    this.peakVx = 0;
    this.peakVy = 0;
    this.peakSpeed = 0;

    // Expose telemetry globally
    window.__telemetry__ = this.getData();
  }

  update(ball, engine) {
    // Frame timing
    const now = Date.now();
    if (this.lastUpdateTime !== null) {
      this.frameDelta = now - this.lastUpdateTime;
    }
    this.lastUpdateTime = now;

    this.frameCount++;
    const elapsed = (now - this.startTime) / 1000;

    if (ball && ball.body) {
      const b = ball.body;

      // Store previous frame data before overwriting
      this.prevBallData = { ...this.ballData };

      this.ballData = {
        x: Math.round(b.position.x * 100) / 100,
        y: Math.round(b.position.y * 100) / 100,
        vx: Math.round(b.velocity.x * 100) / 100,
        vy: Math.round(b.velocity.y * 100) / 100,
        mass: Math.round(b.mass * 100) / 100,
        radius: b.circleRadius || SIM_CONFIG.ballRadius || 20,
        angle: Math.round(b.angle * 1000) / 1000,
        angularVelocity: Math.round(b.angularVelocity * 1000) / 1000,
        inertia: Math.round(b.inertia)
      };

      // Ball exists flag
      this.ballExists = true;

      // Ready flag — set once on first valid ball data
      if (!this.ready) {
        this.ready = true;
        window.__telemetryReady__ = true;
      }

      // Peak tracking
      const absVx = Math.abs(this.ballData.vx);
      const absVy = Math.abs(this.ballData.vy);
      const speed = Math.sqrt(absVx * absVx + absVy * absVy);

      if (absVx > this.peakVx) this.peakVx = absVx;
      if (absVy > this.peakVy) this.peakVy = absVy;
      if (speed > this.peakSpeed) this.peakSpeed = Math.round(speed * 100) / 100;
    }

    // Update global telemetry
    const data = this.getData();
    data.t = Math.round(elapsed * 100) / 100;
    window.__telemetry__ = data;

    // Store history
    this.history.push({ ...data, timestamp: Date.now() });
    if (this.history.length > this.maxHistory) {
      this.history.shift();
    }
  }

  recordCollision() {
    this.collisionCount++;
  }

  addError(error) {
    this.errors.push({
      time: Date.now(),
      message: error
    });
  }

  getData() {
    return {
      t: 0,
      ready: this.ready,
      ballExists: this.ballExists,
      frameDelta: this.frameDelta,
      gravityY: SIM_CONFIG.gravityY,
      gravity: {
        x: SIM_CONFIG.gravityX || 0,
        y: SIM_CONFIG.gravityY
      },
      timeScale: SIM_CONFIG.timeScale ?? 1,
      ball: { ...this.ballData },
      prevBall: this.prevBallData ? { ...this.prevBallData } : null,
      collisions: this.collisionCount,
      frameCount: this.frameCount,
      peakVx: this.peakVx,
      peakVy: this.peakVy,
      peakSpeed: this.peakSpeed,
      config: {
        gravityY: SIM_CONFIG.gravityY,
        gravityX: SIM_CONFIG.gravityX || 0,
        restitution: SIM_CONFIG.restitution,
        friction: SIM_CONFIG.friction,
        frictionAir: SIM_CONFIG.frictionAir,
        collisionMask: SIM_CONFIG.collisionMask,
        boundsEnabled: SIM_CONFIG.boundsEnabled,
        timeScale: SIM_CONFIG.timeScale ?? 1,
        ballMass: SIM_CONFIG.ballMass ?? 1,
        ballRadius: SIM_CONFIG.ballRadius ?? 20,
        ballInertia: SIM_CONFIG.ballInertia
      },
      errors: [...this.errors]
    };
  }

  getHistory() {
    return [...this.history];
  }

  reset() {
    this.startTime = Date.now();
    this.frameCount = 0;
    this.collisionCount = 0;
    this.ballData = { x: 0, y: 0, vx: 0, vy: 0, mass: 0, radius: 0, angle: 0, angularVelocity: 0, inertia: 0 };
    this.errors = [];
    this.history = [];

    // Reset ball exists flag (ready stays true once set)
    this.ballExists = false;

    // Reset frame timing
    this.lastUpdateTime = null;
    this.frameDelta = 0;

    // Reset previous frame data
    this.prevBallData = null;

    // Reset peak tracking
    this.peakVx = 0;
    this.peakVy = 0;
    this.peakSpeed = 0;

    window.__telemetry__ = this.getData();
  }
}

export const telemetry = new TelemetrySystem();
