// GenieGuard: World-Sim CI - Physics Configuration (v2 — Tier 1 + Tier 2)
// Supports runtime override via localStorage for dashboard control

const HEALTHY_DEFAULTS = {
  // Tier 1 targets
  gravityY: 1,
  restitution: 0.6,
  friction: 0.1,
  frictionAir: 0.01,
  collisionMask: 0xFFFFFFFF,
  boundsEnabled: true,
  // Tier 2 targets
  gravityX: 0,
  timeScale: 1,
  ballMass: 1,
  ballRadius: 20,
  ballInertia: null, // null = auto-calculate
};

let _stored = null;
try {
  const raw = localStorage.getItem('genieguard_config');
  if (raw) _stored = JSON.parse(raw);
} catch (e) {}

export const SIM_CONFIG = _stored || { ...HEALTHY_DEFAULTS };
export const HEALTHY_CONFIG = { ...HEALTHY_DEFAULTS };
