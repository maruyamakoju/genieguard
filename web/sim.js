// GenieGuard: World-Sim CI - Enhanced Physics Simulator (v3 — Visual FX Overhaul)
// ─────────────────────────────────────────────────────────────────────────────
// Matter.js 2D physics sim for the GenieGuard hackathon dashboard.
// Runs inside an iframe; exposes telemetry via window.__telemetry__.
// Config is loaded from web/config.js (localStorage-backed).
// ─────────────────────────────────────────────────────────────────────────────

import { SIM_CONFIG } from './config.js';
import { telemetry }  from './telemetry.js';
import { HUD }        from './hud.js';

const { Engine, Render, Runner, Bodies, Body, Composite, Events } = Matter;

// ── Constants ────────────────────────────────────────────────────────────────

const SPAWN_ANIM_DURATION = 300;          // ms — ball grow-in time
const TRAIL_LENGTH        = 8;            // positions remembered per ball
const GLOW_PULSE_SPEED    = 0.004;        // sin-wave speed for glow pulse
const GLOW_PULSE_AMOUNT   = 0.15;         // amplitude of the glow pulse

// ── PhysicsSimulator ─────────────────────────────────────────────────────────

class PhysicsSimulator {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.width     = 960;
    this.height    = 540;
    this.balls     = [];
    this.particles = [];
    this.trails    = new Map();   // body.id → [{x,y}, …]
    this.hud       = null;
    this.hudCanvas = null;
    this.fxCanvas  = null;
    this.fxCtx     = null;
    this.frameTime = 0;           // monotonic time passed to drawFX

    // Game elements
    this.coins     = [];
    this.coinCount = 0;
    this.stars     = Array.from({length: 50}, () => ({
      x: Math.random() * 960,
      y: Math.random() * 320,
      r: Math.random() * 1.2 + 0.3,
      b: 0.3 + Math.random() * 0.5,
      sp: 0.001 + Math.random() * 0.003
    }));

    this.init();
  }

  // ── Initialisation ───────────────────────────────────────────────────────

  init() {
    window.__simReady__ = false;

    this.engine = Engine.create({
      gravity: { x: SIM_CONFIG.gravityX || 0, y: SIM_CONFIG.gravityY }
    });
    // Tier 2: timeScale
    this.engine.timing.timeScale = SIM_CONFIG.timeScale ?? 1;

    this.render = Render.create({
      element: this.container,
      engine:  this.engine,
      options: {
        width:      this.width,
        height:     this.height,
        wireframes: false,
        background: '#0c1525'
      }
    });

    this.createBoundaries();
    this.createPlatforms();
    this.createCoins();
    this.createFXCanvas();
    this.createHUD();
    this.setupCollisionEvents();

    // Stretch all canvases to fill container
    [this.render.canvas, this.fxCanvas, this.hudCanvas].forEach(c => {
      if (c) Object.assign(c.style, { width: '100%', height: '100%', display: 'block' });
    });

    Render.run(this.render);
    this.runner = Runner.create();
    Runner.run(this.runner, this.engine);
    this.updateLoop();
  }

  // ── Boundaries ───────────────────────────────────────────────────────────

  createBoundaries() {
    const opts = (label) => ({
      isStatic: true,
      label,
      friction: SIM_CONFIG.friction,
      render: { fillStyle: label === 'ground' ? '#2a5e1e' : '#0c1525' },
      collisionFilter: { category: 0x0001, mask: SIM_CONFIG.collisionMask }
    });

    this.boundaries = [
      Bodies.rectangle(this.width / 2,  this.height - 15, this.width, 30, opts('ground')),
      Bodies.rectangle(-15,             this.height / 2,  30, this.height, opts('leftWall')),
      Bodies.rectangle(this.width + 15, this.height / 2,  30, this.height, opts('rightWall')),
      Bodies.rectangle(this.width / 2,  -15,              this.width, 30,  opts('ceiling')),
    ];
    Composite.add(this.engine.world, this.boundaries);
  }

  // ── Platforms ────────────────────────────────────────────────────────────

  createPlatforms() {
    const s = { fillStyle: '#3a2a18', strokeStyle: '#4d8b31', lineWidth: 2 };
    const defs = [
      { x: 240, y: 405, w: 200, h: 16 },
      { x: 720, y: 315, w: 220, h: 16 },
      { x: 420, y: 225, w: 180, h: 16 },
      { x: 156, y: 162, w: 140, h: 16, a: -0.15 },
      { x: 816, y: 144, w: 160, h: 16, a:  0.12 },
    ];
    this.platformDefs = defs;   // keep defs for FX drawing
    this.platformBodies = defs.map(p =>
      Bodies.rectangle(p.x, p.y, p.w, p.h, {
        isStatic: true,
        label: 'platform',
        friction: SIM_CONFIG.friction,
        render: s,
        angle: p.a || 0,
        collisionFilter: { category: 0x0001, mask: SIM_CONFIG.collisionMask }
      })
    );
    Composite.add(this.engine.world, this.platformBodies);
  }

  // ── Coins (collectibles) ────────────────────────────────────────────────

  createCoins() {
    const positions = [
      {x:240, y:373}, {x:720, y:283}, {x:420, y:193},
      {x:156, y:130}, {x:816, y:112}, {x:480, y:432},
      {x:600, y:342}, {x:120, y:486}, {x:840, y:486},
      {x:540, y:90},
    ];
    this.coinPositions = positions;
    positions.forEach(p => {
      const coin = Bodies.circle(p.x, p.y, 10, {
        isStatic: true, isSensor: true, label: 'coin',
        render: { fillStyle: '#ffd700', strokeStyle: '#daa520', lineWidth: 2 }
      });
      this.coins.push(coin);
    });
    Composite.add(this.engine.world, this.coins);
  }

  respawnCoins() {
    this.coins.forEach(c => Composite.remove(this.engine.world, c));
    this.coins = [];
    this.coinCount = 0;
    this.createCoins();
  }

  // ── Overlay canvases ─────────────────────────────────────────────────────

  createFXCanvas() {
    this.fxCanvas = document.createElement('canvas');
    Object.assign(this.fxCanvas, { width: this.width, height: this.height });
    Object.assign(this.fxCanvas.style, {
      position: 'absolute', top: '0', left: '0', pointerEvents: 'none'
    });
    this.container.style.position = 'relative';
    this.container.appendChild(this.fxCanvas);
    this.fxCtx = this.fxCanvas.getContext('2d');
  }

  createHUD() {
    this.hudCanvas = document.createElement('canvas');
    Object.assign(this.hudCanvas, { width: this.width, height: this.height });
    Object.assign(this.hudCanvas.style, {
      position: 'absolute', top: '0', left: '0', pointerEvents: 'none'
    });
    this.container.appendChild(this.hudCanvas);
    this.hud = new HUD(this.hudCanvas);
  }

  // ── Collision events ─────────────────────────────────────────────────────

  setupCollisionEvents() {
    Events.on(this.engine, 'collisionStart', (event) => {
      event.pairs.forEach(pair => {
        const a = pair.bodyA;
        const b = pair.bodyB;
        const ball    = a.label === 'ball' ? a : (b.label === 'ball' ? b : null);
        if (!ball) return;

        const surface = a.label !== 'ball' ? a : b;
        if (surface.label === 'ground') telemetry.recordCollision();

        // Coin collection
        if (surface.label === 'coin') {
          Composite.remove(this.engine.world, surface);
          this.coins = this.coins.filter(c => c !== surface);
          this.coinCount++;
          this.spawnParticles(surface.position.x, surface.position.y, 5, 'coin');
          return;
        }

        // Compute collision point
        const s  = pair.collision.supports;
        const cx = s && s[0] ? s[0].x : ball.position.x;
        const cy = s && s[0] ? s[0].y : ball.position.y;

        // Collision velocity (magnitude) drives particle count
        const relVel = Math.hypot(
          ball.velocity.x - (surface.velocity ? surface.velocity.x : 0),
          ball.velocity.y - (surface.velocity ? surface.velocity.y : 0)
        );

        this.spawnParticles(cx, cy, relVel, surface.label);
      });
    });
  }

  // ── Particle system ──────────────────────────────────────────────────────

  /**
   * Spawn impact particles.
   * @param {number} x  - collision x
   * @param {number} y  - collision y
   * @param {number} impactSpeed - relative velocity magnitude
   * @param {string} surfaceLabel - 'ground', 'platform', etc.
   */
  spawnParticles(x, y, impactSpeed = 6, surfaceLabel = '') {
    // Base count scales with impact force (min 8, max 30)
    const count = Math.min(30, Math.max(8, Math.round(8 + impactSpeed * 1.5)));

    // Surface-tinted colour palettes
    const groundColors   = ['#00ff88', '#00cc66', '#88ffbb', '#4dff4d', '#aaffdd'];
    const platformColors = ['#00d4ff', '#00b8e6', '#66e0ff', '#00d4ff', '#99eeff'];
    const coinColors     = ['#ffd700', '#ffaa00', '#fff176', '#ffe082', '#ffffff'];
    const defaultColors  = ['#00ff88', '#00d4ff', '#ff4444', '#ffcc00', '#ff00ff'];

    let palette;
    if (surfaceLabel === 'ground')        palette = groundColors;
    else if (surfaceLabel === 'platform') palette = platformColors;
    else if (surfaceLabel === 'coin')     palette = coinColors;
    else palette = defaultColors;

    for (let i = 0; i < count; i++) {
      const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.5;
      const speed = 2 + Math.random() * 4 + impactSpeed * 0.3;

      // Variety: ~30 % squares, ~20 % tiny sparkle dots, rest normal circles
      const roll = Math.random();
      let shape, sparkle;
      if (roll < 0.3) {
        shape   = 'square';
        sparkle = false;
      } else if (roll < 0.5) {
        shape   = 'dot';
        sparkle = true;      // sparkle = flash bright then fade
      } else {
        shape   = 'circle';
        sparkle = Math.random() < 0.15;
      }

      this.particles.push({
        x, y,
        vx:      Math.cos(angle) * speed,
        vy:      Math.sin(angle) * speed - 2,
        life:    1,
        decay:   0.02 + Math.random() * 0.03,
        size:    shape === 'dot' ? 1 + Math.random() * 1.5 : 2 + Math.random() * 3,
        color:   palette[Math.floor(Math.random() * palette.length)],
        shape,
        sparkle,
        sparklePhase: Math.random() * Math.PI * 2
      });
    }
  }

  // ── Ball spawning (with grow-in animation) ───────────────────────────────

  spawnBall(x = null, y = null) {
    const sx = x ?? this.width / 2;
    const sy = y ?? 80;
    const r  = SIM_CONFIG.ballRadius ?? 20;

    // Create ball at a tiny initial radius so it can grow visually
    const ball = Bodies.circle(sx, sy, r, {
      restitution: SIM_CONFIG.restitution,
      friction:    SIM_CONFIG.friction,
      frictionAir: SIM_CONFIG.frictionAir,
      render: { fillStyle: '#e94560', strokeStyle: '#ff6b8a', lineWidth: 2 },
      label: 'ball',
      collisionFilter: { category: 0x0002, mask: SIM_CONFIG.collisionMask }
    });

    // Tier 2: mass & inertia overrides
    if (SIM_CONFIG.ballMass != null && SIM_CONFIG.ballMass !== 1) {
      Body.setMass(ball, SIM_CONFIG.ballMass);
    }
    if (SIM_CONFIG.ballInertia != null) {
      Body.setInertia(ball, SIM_CONFIG.ballInertia);
    }

    const entry = {
      body:      ball,
      spawnTime: Date.now(),
      targetRadius: r,
      animating: true           // grow-in flag
    };

    // Start at nearly-zero visual scale; physics body stays full-size so
    // collisions work immediately, but the render & FX reflect the animation.
    Body.scale(ball, 0.01, 0.01);
    entry._currentScale = 0.01;

    this.balls.push(entry);
    Composite.add(this.engine.world, ball);
    return ball;
  }

  // ── Reset ────────────────────────────────────────────────────────────────

  reset() {
    this.balls.forEach(b => Composite.remove(this.engine.world, b.body));
    this.balls     = [];
    this.particles = [];
    this.trails.clear();
    this.respawnCoins();
    telemetry.reset();
    this.engine.gravity.y          = SIM_CONFIG.gravityY;
    this.engine.gravity.x          = SIM_CONFIG.gravityX || 0;
    this.engine.timing.timeScale   = SIM_CONFIG.timeScale ?? 1;
  }

  // ── Main loop ────────────────────────────────────────────────────────────

  updateLoop() {
    let firstFrame = true;

    const update = () => {
      const now = Date.now();
      this.frameTime = now;

      // Animate ball spawn (scale from tiny to full over SPAWN_ANIM_DURATION)
      this.balls.forEach(entry => {
        if (!entry.animating) return;
        const elapsed = now - entry.spawnTime;
        const t = Math.min(elapsed / SPAWN_ANIM_DURATION, 1);
        // Ease-out cubic
        const eased = 1 - Math.pow(1 - t, 3);
        const desired = 0.01 + eased * 0.99;           // 0.01 → 1.0
        const factor  = desired / entry._currentScale;
        Body.scale(entry.body, factor, factor);
        entry._currentScale = desired;
        if (t >= 1) entry.animating = false;
      });

      // Record trail positions
      this.balls.forEach(entry => {
        const id = entry.body.id;
        if (!this.trails.has(id)) this.trails.set(id, []);
        const trail = this.trails.get(id);
        const p = entry.body.position;
        trail.push({ x: p.x, y: p.y });
        if (trail.length > TRAIL_LENGTH) trail.shift();
      });

      // Telemetry
      const pb = this.balls.length > 0 ? this.balls[0] : null;
      telemetry.update(pb, this.engine);

      this.checkBounds();
      this.drawFX();

      // HUD
      const ctx = this.hudCanvas.getContext('2d');
      ctx.clearRect(0, 0, this.width, this.height);
      this.hud.draw(window.__telemetry__);

      // Ready signal after first rendered frame
      if (firstFrame) {
        firstFrame = false;
        window.__simReady__ = true;
      }

      requestAnimationFrame(update);
    };

    update();
  }

  // ── FX rendering ─────────────────────────────────────────────────────────

  drawFX() {
    const ctx = this.fxCtx;
    const now = this.frameTime;

    // Fade previous frame (motion-blur style)
    ctx.fillStyle = 'rgba(12,21,37,0.15)';
    ctx.fillRect(0, 0, this.width, this.height);

    // ── Stars ────────────────────────────────────────────────────────────
    this.drawStars(ctx, now);

    // ── Ground glow ────────────────────────────────────────────────────────
    this.drawGroundGlow(ctx);

    // ── Platform enhancements ──────────────────────────────────────────────
    this.drawPlatformEffects(ctx);

    // ── Coins (glow) ─────────────────────────────────────────────────────
    this.drawCoinGlow(ctx, now);

    // ── Ball trails ────────────────────────────────────────────────────────
    this.drawTrails(ctx);

    // ── Ball glow (with pulsing) ───────────────────────────────────────────
    this.drawBallGlow(ctx, now);

    // ── Ball face (character) ─────────────────────────────────────────────
    this.drawBallFace(ctx);

    // ── Particles ──────────────────────────────────────────────────────────
    this.drawParticles(ctx, now);

    // ── Coin counter ─────────────────────────────────────────────────────
    this.drawCoinCounter(ctx);
  }

  // ── Ground glow effect ───────────────────────────────────────────────────

  drawGroundGlow(ctx) {
    const groundY = this.height - 30;
    // Grass glow
    const grad = ctx.createLinearGradient(0, groundY - 20, 0, groundY);
    grad.addColorStop(0, 'rgba(45,110,30,0)');
    grad.addColorStop(0.6, 'rgba(45,110,30,0.08)');
    grad.addColorStop(1, 'rgba(45,140,30,0.2)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, groundY - 20, this.width, 20);

    // Grass top line
    ctx.strokeStyle = 'rgba(80,200,50,0.35)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, groundY);
    ctx.lineTo(this.width, groundY);
    ctx.stroke();

    // Grass blades
    ctx.strokeStyle = 'rgba(80,180,40,0.3)';
    ctx.lineWidth = 1;
    for (let x = 5; x < this.width; x += 18) {
      const h = 4 + Math.sin(x * 0.3) * 3;
      ctx.beginPath();
      ctx.moveTo(x, groundY);
      ctx.lineTo(x + 2, groundY - h);
      ctx.stroke();
    }
  }

  // ── Platform visual enhancements ─────────────────────────────────────────

  drawPlatformEffects(ctx) {
    this.platformBodies.forEach((body, idx) => {
      const def = this.platformDefs[idx];
      const hw  = def.w / 2;
      const hh  = def.h / 2;
      const a   = body.angle;
      const px  = body.position.x;
      const py  = body.position.y;

      ctx.save();
      ctx.translate(px, py);
      ctx.rotate(a);

      // Grass top gradient on platform
      const grad = ctx.createLinearGradient(0, -hh, 0, hh);
      grad.addColorStop(0, 'rgba(77,139,49,0.25)');
      grad.addColorStop(0.4, 'rgba(58,42,24,0.1)');
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = grad;
      ctx.fillRect(-hw, -hh, def.w, def.h);

      // Grass glow line on top edge
      ctx.strokeStyle = 'rgba(80,200,50,0.45)';
      ctx.lineWidth   = 2;
      ctx.shadowColor  = 'rgba(80,200,50,0.3)';
      ctx.shadowBlur   = 4;
      ctx.beginPath();
      ctx.moveTo(-hw, -hh);
      ctx.lineTo(hw, -hh);
      ctx.stroke();
      ctx.shadowBlur = 0;

      ctx.restore();
    });
  }

  // ── Motion trail ─────────────────────────────────────────────────────────

  drawTrails(ctx) {
    this.balls.forEach(entry => {
      const trail = this.trails.get(entry.body.id);
      if (!trail || trail.length < 2) return;

      const r = entry.targetRadius ?? (SIM_CONFIG.ballRadius ?? 20);
      // During spawn animation, scale the trail radius too
      const scale = entry.animating ? (entry._currentScale || 1) : 1;

      for (let i = 0; i < trail.length; i++) {
        // Fade: oldest = nearly invisible, newest = most visible
        const frac = i / trail.length;            // 0 (oldest) → ~1 (newest)
        const alpha = frac * 0.35;                // max 0.35 opacity
        const trailR = r * scale * (0.3 + frac * 0.7);
        ctx.beginPath();
        ctx.arc(trail[i].x, trail[i].y, trailR, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(233,69,96,${alpha.toFixed(3)})`;
        ctx.fill();
      }
    });
  }

  // ── Ball glow with sin-wave pulse ────────────────────────────────────────

  drawBallGlow(ctx, now) {
    const pulse = Math.sin(now * GLOW_PULSE_SPEED);   // -1 → 1

    this.balls.forEach(entry => {
      const b  = entry.body;
      const p  = b.position;
      const sp = Math.hypot(b.velocity.x, b.velocity.y);
      const al = Math.min(sp / 20, 0.8);

      // Pulse modulates size & opacity slightly
      const pulseSizeOffset    = pulse * GLOW_PULSE_AMOUNT * 8;
      const pulseOpacityOffset = pulse * GLOW_PULSE_AMOUNT * 0.12;

      // During spawn animation, scale glow to match visible size
      const scale = entry.animating ? (entry._currentScale || 1) : 1;

      // Inner glow
      const innerR = (10 + sp * 0.3 + pulseSizeOffset) * scale;
      ctx.beginPath();
      ctx.arc(p.x, p.y, Math.max(1, innerR), 0, Math.PI * 2);
      ctx.fillStyle = `rgba(233,69,96,${Math.max(0, al * 0.4 + pulseOpacityOffset).toFixed(3)})`;
      ctx.fill();

      // Outer radial gradient glow
      const outerR = (30 + sp + pulseSizeOffset * 2) * scale;
      const safeOuterR = Math.max(1, outerR);
      const g = ctx.createRadialGradient(p.x, p.y, 5 * scale, p.x, p.y, safeOuterR);
      g.addColorStop(0, `rgba(233,69,96,${Math.max(0, al * 0.3 + pulseOpacityOffset).toFixed(3)})`);
      g.addColorStop(1, 'rgba(233,69,96,0)');
      ctx.beginPath();
      ctx.arc(p.x, p.y, safeOuterR, 0, Math.PI * 2);
      ctx.fillStyle = g;
      ctx.fill();
    });
  }

  // ── Particle rendering ───────────────────────────────────────────────────

  drawParticles(ctx, now) {
    this.particles = this.particles.filter(p => {
      // Physics step
      p.x  += p.vx;
      p.y  += p.vy;
      p.vy += 0.1;
      p.life -= p.decay;
      if (p.life <= 0) return false;

      // Sparkle: brightness oscillates then fades
      let alpha = p.life;
      if (p.sparkle) {
        const flash = 0.5 + 0.5 * Math.sin(now * 0.02 + p.sparklePhase);
        alpha = p.life * (0.5 + flash * 0.8);   // brighter pulses
      }
      alpha = Math.min(1, Math.max(0, alpha));

      ctx.globalAlpha = alpha;
      ctx.fillStyle   = p.color;

      const sz = p.size * p.life;

      if (p.shape === 'square') {
        ctx.fillRect(p.x - sz / 2, p.y - sz / 2, sz, sz);
      } else {
        // 'circle' or 'dot'
        ctx.beginPath();
        ctx.arc(p.x, p.y, sz, 0, Math.PI * 2);
        ctx.fill();
      }

      // Extra sparkle bloom for sparkle particles
      if (p.sparkle && alpha > 0.6) {
        ctx.globalAlpha = (alpha - 0.6) * 1.5;
        ctx.beginPath();
        ctx.arc(p.x, p.y, sz * 2, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255,255,255,0.25)';
        ctx.fill();
      }

      ctx.globalAlpha = 1;
      return true;
    });
  }

  // ── Stars (twinkling night sky) ─────────────────────────────────────────

  drawStars(ctx, now) {
    this.stars.forEach(s => {
      const twinkle = 0.5 + 0.5 * Math.sin(now * s.sp + s.x);
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${(s.b * twinkle).toFixed(3)})`;
      ctx.fill();
    });
  }

  // ── Ball character face ────────────────────────────────────────────────

  drawBallFace(ctx) {
    this.balls.forEach(entry => {
      const b = entry.body;
      const p = b.position;
      const r = entry.targetRadius ?? (SIM_CONFIG.ballRadius ?? 20);
      const scale = entry.animating ? (entry._currentScale || 1) : 1;
      const radius = r * scale;
      if (radius < 5) return;  // too small for face

      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(b.angle);

      const eOff = radius * 0.28;
      const eR = radius * 0.2;
      const pR = radius * 0.11;

      // Eyes (white)
      ctx.fillStyle = '#fff';
      ctx.beginPath();
      ctx.arc(-eOff, -radius * 0.12, eR, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(eOff, -radius * 0.12, eR, 0, Math.PI * 2);
      ctx.fill();

      // Pupils (dark)
      ctx.fillStyle = '#1a1a2e';
      ctx.beginPath();
      ctx.arc(-eOff + pR * 0.3, -radius * 0.1, pR, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(eOff + pR * 0.3, -radius * 0.1, pR, 0, Math.PI * 2);
      ctx.fill();

      // Eye shine
      ctx.fillStyle = 'rgba(255,255,255,0.7)';
      ctx.beginPath();
      ctx.arc(-eOff - pR * 0.4, -radius * 0.18, pR * 0.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(eOff - pR * 0.4, -radius * 0.18, pR * 0.5, 0, Math.PI * 2);
      ctx.fill();

      // Smile
      if (radius >= 12) {
        ctx.beginPath();
        ctx.arc(0, radius * 0.08, radius * 0.22, 0.15 * Math.PI, 0.85 * Math.PI);
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = Math.max(1, radius * 0.07);
        ctx.lineCap = 'round';
        ctx.stroke();
      }

      ctx.restore();
    });
  }

  // ── Coin glow rendering ────────────────────────────────────────────────

  drawCoinGlow(ctx, now) {
    this.coins.forEach(coin => {
      const p = coin.position;
      const pulse = 0.6 + 0.4 * Math.sin(now * 0.004 + p.x * 0.1);

      // Outer glow
      const g = ctx.createRadialGradient(p.x, p.y, 4, p.x, p.y, 22);
      g.addColorStop(0, `rgba(255,215,0,${(0.25 * pulse).toFixed(3)})`);
      g.addColorStop(1, 'rgba(255,215,0,0)');
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 22, 0, Math.PI * 2);
      ctx.fill();

      // Sparkle cross
      const sparkle = Math.sin(now * 0.006 + p.y);
      if (sparkle > 0.7) {
        ctx.strokeStyle = `rgba(255,255,255,${((sparkle - 0.7) * 2).toFixed(3)})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(p.x - 6, p.y); ctx.lineTo(p.x + 6, p.y);
        ctx.moveTo(p.x, p.y - 6); ctx.lineTo(p.x, p.y + 6);
        ctx.stroke();
      }
    });
  }

  // ── Coin counter display ───────────────────────────────────────────────

  drawCoinCounter(ctx) {
    ctx.save();
    ctx.font = 'bold 16px "JetBrains Mono", monospace';
    ctx.fillStyle = '#ffd700';
    ctx.shadowColor = '#ffd700';
    ctx.shadowBlur = 6;
    ctx.textAlign = 'right';
    ctx.fillText(`🪙 × ${this.coinCount}`, this.width - 16, 28);
    ctx.shadowBlur = 0;
    ctx.restore();
  }

  // ── Bounds checking ──────────────────────────────────────────────────────

  checkBounds() {
    if (!SIM_CONFIG.boundsEnabled) return;
    this.balls.forEach(b => {
      const p = b.body.position;
      if (p.x < -100 || p.x > this.width + 100 || p.y < -100 || p.y > this.height + 100) {
        telemetry.addError(`Ball escaped at (${p.x.toFixed(0)},${p.y.toFixed(0)})`);
      }
    });
  }
}

// ── Module bootstrap ───────────────────────────────────────────────────────

let simulator = null;

function initSimulator() {
  simulator = new PhysicsSimulator('simulator-container');
  window.simulator = simulator;
  window.spawnBall = () => simulator.spawnBall();
  window.resetSim  = () => simulator.reset();
}

export { PhysicsSimulator, initSimulator };

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSimulator);
} else {
  initSimulator();
}
