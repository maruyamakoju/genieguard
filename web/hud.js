// GenieGuard: World-Sim CI - Enhanced HUD Overlay (v3 — Tier 2 Prominent)

export class HUD {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');

    // Sparkline Y-history buffer (last 30 frames)
    this.yHistory = [];
    this.maxHistory = 30;

    // Pulsing border animation state
    this._pulsePhase = 0;
  }

  // ─────────────────────────────────────────────
  //  Main draw entry point
  // ─────────────────────────────────────────────
  draw(telemetry) {
    const ctx = this.ctx;
    const data = window.__telemetry__ || telemetry;
    if (!data) return;

    // Layout constants
    const p = 10;            // panel left/top padding
    const lh = 18;           // line height
    const panelW = 280;      // panel width
    const innerX = p + 10;   // text left edge
    const colX = p + 140;    // second column left edge
    const badgeRowH = 22;    // height for a badge row
    const sparkH = 50;       // sparkline chart height
    const sectionGap = 8;    // gap around separator lines

    // ── Pre-compute bug/anomaly lists for badge display ──
    const t1Bugs = this._computeT1Bugs(data);
    const t2Anomalies = this._computeT2Anomalies(data);
    const hasBugs = t1Bugs.length > 0 || t2Anomalies.length > 0;

    // ── Pre-compute Tier 2 highlight lines ──
    const tier2Lines = this._computeTier2Lines(data);

    // ── Update sparkline history ──
    if (data.ball && data.ball.y != null) {
      this.yHistory.push(data.ball.y);
      if (this.yHistory.length > this.maxHistory) {
        this.yHistory.shift();
      }
    }

    // ── Calculate dynamic panel height ──
    let contentH = 0;
    contentH += lh + 2;                          // title
    contentH += lh;                               // time + timeScale row
    contentH += lh;                               // gravY + gravX row
    if (data.ball && (data.ball.x != null || data.ball.y != null)) {
      contentH += lh;                             // pos
      contentH += lh;                             // vel
      if (data.ball.mass) {
        contentH += lh;                           // mass + radius
        contentH += lh;                           // omega + inertia
      }
    } else {
      contentH += lh * 2;                         // "No ball spawned"
    }
    contentH += sectionGap;                       // separator before Tier 2
    if (tier2Lines.length > 0) {
      contentH += lh * tier2Lines.length;         // Tier 2 highlight lines
      contentH += sectionGap;                     // separator after Tier 2
    }
    contentH += lh;                               // collisions
    contentH += lh;                               // bug status text
    contentH += sectionGap;                       // separator before badges
    contentH += badgeRowH;                        // T1 badge row
    contentH += badgeRowH;                        // T2 badge row
    contentH += sectionGap;                       // separator before sparkline
    contentH += sparkH + 4;                       // sparkline
    const panelH = contentH + p * 2;

    // ── Advance pulse animation ──
    this._pulsePhase = (this._pulsePhase + 0.05) % (Math.PI * 2);

    // ── Panel background: header band + body ──
    const headerH = lh + 6;

    // Body background
    ctx.fillStyle = 'rgba(6, 6, 15, 0.82)';
    this.roundRect(ctx, p, p, panelW, panelH, 8);
    ctx.fill();

    // Header background (slightly lighter)
    ctx.save();
    ctx.beginPath();
    ctx.rect(p, p, panelW, headerH + 8);
    ctx.clip();
    ctx.fillStyle = 'rgba(12, 12, 28, 0.95)';
    this.roundRect(ctx, p, p, panelW, panelH, 8);
    ctx.fill();
    ctx.restore();

    // ── Panel border (pulsing when bugs detected) ──
    if (hasBugs) {
      const pulseAlpha = 0.35 + 0.45 * (0.5 + 0.5 * Math.sin(this._pulsePhase));
      ctx.strokeStyle = `rgba(255, 68, 68, ${pulseAlpha.toFixed(2)})`;
      ctx.lineWidth = 2;
    } else {
      ctx.strokeStyle = '#00ff8844';
      ctx.lineWidth = 1;
    }
    this.roundRect(ctx, p, p, panelW, panelH, 8);
    ctx.stroke();

    // ── Title ──
    let y = p + lh;
    ctx.fillStyle = '#00ff88';
    ctx.font = 'bold 12px JetBrains Mono, monospace';
    ctx.fillText('TELEMETRY', innerX, y);
    y += lh + 2;

    // ── Data section ──
    ctx.font = '11px JetBrains Mono, monospace';

    // Time
    ctx.fillStyle = '#888';
    ctx.fillText(`t: ${(data.t || 0).toFixed(2)}s`, innerX, y);

    // TimeScale (on same row, second column)
    const ts = data.timeScale ?? data.config?.timeScale ?? 1;
    const tsBad = ts < 0.5 || ts > 2;
    ctx.fillStyle = tsBad ? '#ff4444' : '#555';
    ctx.fillText(`tScale: ${ts}`, colX, y);
    y += lh;

    // Gravity Y
    const gravBad = data.gravityY < 0;
    ctx.fillStyle = gravBad ? '#ff4444' : '#e0e0e0';
    ctx.fillText(`gravY: ${data.gravityY}`, innerX, y);

    // Gravity X
    const gx = data.gravity?.x ?? data.config?.gravityX ?? 0;
    const gxBad = Math.abs(gx) > 0.5;
    ctx.fillStyle = gxBad ? '#ff4444' : '#555';
    ctx.fillText(`gravX: ${gx}`, colX, y);
    y += lh;

    // Ball position & velocity
    if (data.ball && (data.ball.x != null || data.ball.y != null)) {
      ctx.fillStyle = '#e0e0e0';
      ctx.fillText(`pos: (${data.ball.x.toFixed(0)}, ${data.ball.y.toFixed(0)})`, innerX, y);
      y += lh;

      const speed = Math.sqrt(data.ball.vx ** 2 + data.ball.vy ** 2);
      const fast = speed > 40;
      ctx.fillStyle = fast ? '#ff4444' : '#e0e0e0';
      ctx.fillText(`vel: (${data.ball.vx.toFixed(1)}, ${data.ball.vy.toFixed(1)})`, innerX, y);
      y += lh;

      // Tier 2: Mass & Radius
      if (data.ball.mass) {
        const massBad = data.ball.mass > 100;
        const radiusBad = data.ball.radius < 8 || data.ball.radius > 50;
        ctx.fillStyle = massBad ? '#ff4444' : '#aaa';
        ctx.fillText(`mass: ${data.ball.mass.toFixed(1)}`, innerX, y);
        ctx.fillStyle = radiusBad ? '#ff4444' : '#aaa';
        ctx.fillText(`r: ${data.ball.radius}`, colX, y);
        y += lh;

        // Tier 2: Rotation & Inertia
        const aBad = Math.abs(data.ball.angularVelocity) > 0.5;
        const iBad = data.ball.inertia > 10000;
        ctx.fillStyle = aBad ? '#ff4444' : '#555';
        ctx.fillText(`\u03C9: ${data.ball.angularVelocity.toFixed(3)}`, innerX, y);
        ctx.fillStyle = iBad ? '#ffcc00' : '#555';
        ctx.fillText(`I: ${data.ball.inertia > 9999 ? data.ball.inertia.toExponential(1) : data.ball.inertia.toFixed(0)}`, colX, y);
        y += lh;
      }
    } else {
      ctx.fillStyle = '#555';
      ctx.fillText('No ball spawned', innerX, y);
      y += lh * 2;
    }

    // ── Separator: before Tier 2 highlights ──
    if (tier2Lines.length > 0) {
      y += sectionGap / 2;
      this._drawSeparator(ctx, innerX, y, panelW - 30);
      y += sectionGap / 2;

      // ── Tier 2 prominent parameter highlights ──
      ctx.font = 'bold 11px JetBrains Mono, monospace';
      for (const line of tier2Lines) {
        ctx.fillStyle = line.color;
        ctx.fillText(line.text, innerX, y);
        y += lh;
      }
      ctx.font = '11px JetBrains Mono, monospace';
    }

    // ── Separator: before collisions ──
    y += sectionGap / 2;
    this._drawSeparator(ctx, innerX, y, panelW - 30);
    y += sectionGap / 2;

    // ── Collisions ──
    ctx.fillStyle = '#e0e0e0';
    ctx.font = '11px JetBrains Mono, monospace';
    ctx.fillText(`collisions: ${data.collisions || 0}`, innerX, y);
    y += lh;

    // ── Bug status text ──
    if (data.config) {
      const allIssues = [...t1Bugs, ...t2Anomalies];
      if (allIssues.length > 0) {
        ctx.fillStyle = '#ff4444';
        ctx.font = 'bold 11px JetBrains Mono, monospace';
        ctx.fillText(`BUGS: ${allIssues.join(' ')}`, innerX, y);
      } else {
        ctx.fillStyle = '#00ff88';
        ctx.font = 'bold 11px JetBrains Mono, monospace';
        ctx.fillText('STATUS: HEALTHY', innerX, y);
      }
    }
    y += lh;

    // ── Separator: before badge rows ──
    y += sectionGap / 2;
    this._drawSeparator(ctx, innerX, y, panelW - 30);
    y += sectionGap / 2;

    // ── Tier badge indicators ──
    this._drawBadgeRow(ctx, innerX, y, 'T1:', ['B1', 'B2', 'B3', 'B4', 'B5'], t1Bugs, '#00ff88', '#ff4444');
    y += badgeRowH;
    this._drawBadgeRow(ctx, innerX, y, 'T2:', ['U1', 'U2', 'U3', 'U4', 'U5'], t2Anomalies, '#00ff88', '#ff9900');
    y += badgeRowH;

    // ── Separator: before sparkline ──
    y += sectionGap / 2;
    this._drawSeparator(ctx, innerX, y, panelW - 30);
    y += sectionGap / 2;

    // ── Mini sparkline (last 30 Y values) ──
    this._drawSparkline(ctx, innerX, y, panelW - 30, sparkH);
  }

  // ─────────────────────────────────────────────
  //  Tier 1 bug detection
  // ─────────────────────────────────────────────
  _computeT1Bugs(data) {
    const bugs = [];
    if (!data.config) return bugs;
    if (data.config.gravityY < 0) bugs.push('B1');
    if (data.config.collisionMask === 0) bugs.push('B2');
    if (data.config.restitution > 1.0) bugs.push('B3');
    if (data.config.friction === 0 && data.config.frictionAir === 0) bugs.push('B4');
    if (!data.config.boundsEnabled) bugs.push('B5');
    return bugs;
  }

  // ─────────────────────────────────────────────
  //  Tier 2 anomaly detection
  // ─────────────────────────────────────────────
  _computeT2Anomalies(data) {
    const anomalies = [];
    if (!data.config) return anomalies;
    if (data.config.timeScale != null && data.config.timeScale < 0.5) anomalies.push('U1');
    if (Math.abs(data.config.gravityX || 0) > 0.5) anomalies.push('U2');
    if (data.config.ballMass != null && data.config.ballMass > 100) anomalies.push('U3');
    if (data.config.ballInertia != null && data.config.ballInertia > 10000) anomalies.push('U4');
    if (data.config.ballRadius != null && data.config.ballRadius < 8) anomalies.push('U5');
    return anomalies;
  }

  // ─────────────────────────────────────────────
  //  Tier 2 prominent parameter highlight lines
  //  Shows non-default Tier 2 values prominently
  // ─────────────────────────────────────────────
  _computeTier2Lines(data) {
    const lines = [];

    // timeScale != 1
    const ts = data.timeScale ?? data.config?.timeScale ?? 1;
    if (ts !== 1) {
      const severe = ts < 0.5 || ts > 2;
      lines.push({
        text: `\u26A0 timeScale: ${ts}`,
        color: severe ? '#ff4444' : '#ffcc00',
      });
    }

    // gravityX != 0
    const gx = data.gravity?.x ?? data.config?.gravityX ?? 0;
    if (gx !== 0) {
      const severe = Math.abs(gx) > 0.5;
      lines.push({
        text: `\u26A0 gravityX: ${gx}`,
        color: severe ? '#ff4444' : '#ffcc00',
      });
    }

    // mass != 1
    const mass = data.ball?.mass ?? data.config?.ballMass ?? 1;
    if (mass !== 1) {
      const severe = mass > 100;
      lines.push({
        text: `\u26A0 mass: ${typeof mass === 'number' ? mass.toFixed(1) : mass}`,
        color: severe ? '#ff4444' : '#ffcc00',
      });
    }

    // radius != 20
    const radius = data.ball?.radius ?? data.config?.ballRadius ?? 20;
    if (radius !== 20) {
      const severe = radius < 8 || radius > 50;
      lines.push({
        text: `\u26A0 radius: ${radius}`,
        color: severe ? '#ff4444' : '#ffcc00',
      });
    }

    // inertia not auto (heuristic: present and > 0 means manually set)
    const inertia = data.ball?.inertia ?? data.config?.ballInertia ?? null;
    if (inertia != null && inertia > 10000) {
      lines.push({
        text: `\u26A0 inertia: ${inertia > 9999 ? inertia.toExponential(1) : inertia.toFixed(0)}`,
        color: '#ffcc00',
      });
    }

    return lines;
  }

  // ─────────────────────────────────────────────
  //  Draw a thin horizontal separator line
  // ─────────────────────────────────────────────
  _drawSeparator(ctx, x, y, w) {
    ctx.save();
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + w, y);
    ctx.stroke();
    ctx.restore();
  }

  // ─────────────────────────────────────────────
  //  Draw a row of colored badge indicators
  //  Labels like "T1:" followed by small colored
  //  rounded rects with the bug/anomaly ID text.
  // ─────────────────────────────────────────────
  _drawBadgeRow(ctx, x, y, label, allIds, activeIds, okColor, badColor) {
    ctx.save();
    ctx.font = 'bold 10px JetBrains Mono, monospace';

    // Row label
    ctx.fillStyle = '#888';
    ctx.fillText(label, x, y + 12);

    let bx = x + 30;
    const badgeW = 32;
    const badgeH = 16;
    const gap = 6;

    for (const id of allIds) {
      const isBad = activeIds.includes(id);
      const bgColor = isBad ? badColor : okColor;

      // Badge background (small rounded rect)
      ctx.fillStyle = bgColor;
      ctx.globalAlpha = isBad ? 0.9 : 0.25;
      this.roundRect(ctx, bx, y, badgeW, badgeH, 4);
      ctx.fill();
      ctx.globalAlpha = 1.0;

      // Badge text
      ctx.fillStyle = isBad ? '#fff' : 'rgba(255,255,255,0.6)';
      ctx.fillText(id, bx + 7, y + 12);

      bx += badgeW + gap;
    }

    ctx.restore();
  }

  // ─────────────────────────────────────────────
  //  Mini sparkline: last 30 Y values, cyan line
  // ─────────────────────────────────────────────
  _drawSparkline(ctx, x, y, w, h) {
    const hist = this.yHistory;
    if (hist.length < 2) {
      ctx.fillStyle = '#333';
      ctx.font = '9px JetBrains Mono, monospace';
      ctx.fillText('sparkline: awaiting data...', x, y + h / 2 + 3);
      return;
    }

    // Determine Y range from history
    let minY = Infinity;
    let maxY = -Infinity;
    for (const v of hist) {
      if (v < minY) minY = v;
      if (v > maxY) maxY = v;
    }
    // Avoid flat line when range is zero
    if (maxY - minY < 1) {
      minY -= 0.5;
      maxY += 0.5;
    }

    const rangeY = maxY - minY;
    const stepX = w / (this.maxHistory - 1);

    // Subtle background for sparkline area
    ctx.save();
    ctx.fillStyle = 'rgba(0, 255, 255, 0.04)';
    ctx.fillRect(x, y, w, h);

    // Draw the sparkline path
    ctx.strokeStyle = '#00e5ff';
    ctx.lineWidth = 1.5;
    ctx.lineJoin = 'round';
    ctx.beginPath();

    for (let i = 0; i < hist.length; i++) {
      // Map Y position: higher canvas-Y = lower on screen, invert for intuitive display
      const px = x + i * stepX;
      const py = y + h - ((hist[i] - minY) / rangeY) * h;
      if (i === 0) {
        ctx.moveTo(px, py);
      } else {
        ctx.lineTo(px, py);
      }
    }
    ctx.stroke();

    // Label
    ctx.fillStyle = '#00e5ff';
    ctx.globalAlpha = 0.5;
    ctx.font = '8px JetBrains Mono, monospace';
    ctx.fillText('Y trajectory', x + 2, y + 8);
    ctx.restore();
  }

  // ─────────────────────────────────────────────
  //  Rounded rectangle path helper
  // ─────────────────────────────────────────────
  roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }
}
