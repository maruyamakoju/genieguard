# GenieGuard: QA for the Vibe-Coding Era

> **AI writes the game. AI also QA's the game.**

In the age of vibe coding — where Cursor, Claude, and Copilot generate entire games in minutes — **nobody writes tests for the output**. Physics parameters are wrong, collisions don't work, gravity is inverted... and there's no QA engineer in the loop.

**GenieGuard** is a closed-loop CI agent that **automatically detects, diagnoses, and self-repairs** broken physics in AI-generated games. It watches the running simulation, spots what's wrong, and fixes it — without human intervention.

---

## Why This Matters

Traditional game dev has unit tests, QA teams, and physics engine expertise. Vibe coding has none of that:

| Traditional Dev | Vibe Coding |
|---|---|
| Physics engineer tunes parameters | AI generates config, nobody checks |
| QA team plays and reports bugs | Ship it and hope for the best |
| Unit tests catch regressions | No tests written at all |
| Bugs found in days/weeks | Bugs shipped instantly to users |

GenieGuard fills this gap: **the AI that QA's what AI built.**

---

## How It Works

### 2-Tier Architecture

**Tier 1 — Known Bug Patterns (Catalog Repair)**
Invariant checks detect common physics bugs (gravity inversion, collision disabled, etc.) and apply pre-defined patches instantly. Fast and deterministic.

**Tier 2 — Unknown Bugs (Multi-Agent VLM Reasoning)**
For bugs GenieGuard has never seen before, three AI agents work together:

```
┌──────────────────────────────────────────────┐
│           Tier 2: 3-Agent VLM Pipeline       │
│                                              │
│  Agent 1: Vision Analyst ──┐                 │
│    (screenshots × 3)       ├→ Agent 3:       │
│  Agent 2: Physics Analyst ─┘  Repair         │
│    (telemetry + config)       Synthesizer    │
│                               ↓              │
│                          JSON Patch           │
│                               ↓              │
│                     Sandbox Validation        │
│                    (whitelist + range)         │
└──────────────────────────────────────────────┘
```

- **Vision Analyst** — looks at 3 consecutive screenshots, spots visual anomalies
- **Physics Analyst** — analyzes telemetry data and config values against known-good defaults
- **Repair Synthesizer** — cross-validates both agents' findings, generates a minimal safe patch

Patches are **never raw code** — only config diffs, gated by a sandbox whitelist with value-range validation.

### Self-Reflection Loop

If repair fails verification, GenieGuard re-diagnoses with the failure context and retries. The system learns from its own mistakes within a single run.

### Full Pipeline

```
Inject Bug → Collect Telemetry + Screenshots
           → Tier 1 Invariant Check → Catalog Patch
           → Tier 2 VLM Analysis → Sandbox Patch
           → Re-verify all 10 invariants
           → Self-Reflection if failed
           → ✅ Ship or ⚠ Flag
```

---

## Live Dashboard Demo

Open `web/dashboard.html` in a browser and press **"Start Auto Demo"**.

```
Act 1: Known Bug → Tier 1 Catalog Repair
Act 2: Unknown Bug → Tier 2 Multi-Agent VLM Reasoning + Self-Reflection
```

**Free Mode** — Adjust any physics parameter via sliders and challenge GenieGuard to repair it with pure AI reasoning. No pre-defined patches. No hints.

The dashboard supports **JP/EN language toggle** for international demos.

---

## Supported Games

| Game | Engine | Bug Types |
|------|--------|-----------|
| 2D Physics Sandbox | Matter.js | Gravity, collision, restitution, friction, bounds, mass, inertia, radius, time scale |
| STG Shooter | Custom | Bullet speed, fire rate, spawn interval, enemy speed, player speed, hitbox radius |

### Bug Examples

**Tier 1 — Known (instant catalog fix):**
Gravity inversion, collision disabled, infinite bounce, zero friction, bounds off, bullet freeze, hitbox gone, fire disabled, player/enemy freeze

**Tier 2 — Unknown (VLM reasoning required):**
Time frozen, lateral gravity, super-heavy ball, locked inertia, tiny ball, enemy swarm, slow bullets, hyper-fast enemies, giant hitbox, bullet spam

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Start the dev server

```bash
python server.py
```

Opens http://localhost:8080 in your browser.

### 3. Run the demo

**Option A: Dashboard UI**
```bash
python server.py --dashboard
```

**Option B: CLI**
```bash
python genieguard.py              # Full pipeline
python genieguard.py --no-break   # Test current state
python genieguard.py --specific B1 B3  # Inject specific bugs
python genieguard.py --headless   # Headless mode
```

---

## Project Structure

```
genieguard/
├── web/                        # Web simulators
│   ├── index.html              # Physics simulator (Matter.js)
│   ├── stg.html                # STG shooter game
│   ├── dashboard.html          # Demo dashboard (JP/EN)
│   ├── sim.js / config.js      # Physics engine + parameters
│   ├── telemetry.js / hud.js   # Telemetry + HUD overlay
│
├── genieguard/                 # Python modules
│   ├── random_breaker.py       # Bug injection
│   ├── telemetry_collector.py  # Data collection
│   ├── invariant_checker.py    # Numeric invariant checks
│   ├── patch_selector.py       # LLM patch selection
│   ├── patch_applier.py        # Patch application
│   └── evidence_exporter.py    # Evidence export
│
├── genieguard.py               # Main CLI
├── server.py                   # Dev server
└── data/patch_catalog.json     # Patch catalog
```

## Design Principles

1. **Telemetry-driven detection** — PASS/FAIL by numeric invariants, not VLM opinion
2. **No code generation** — Tier 1 selects patch IDs; Tier 2 outputs config diffs only
3. **Sandbox everything** — AI patches are gated by whitelist + value-range validation
4. **Self-Reflection** — Failed repairs trigger re-diagnosis, not just retry
5. **Multi-game** — Same pipeline works for physics sims and shooters

## License

MIT License
