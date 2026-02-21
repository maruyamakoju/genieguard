# GenieGuard: World-Sim CI

**A closed-loop CI pipeline that automatically audits and self-repairs physics in AI-generated games/simulators.**

GenieGuard injects physics bugs into a Matter.js world or an STG shooter, collects telemetry + screenshots, and diagnoses issues with Gemini 3.1 Pro Preview via a **2-Tier architecture**:

- **Tier 1** applies catalog patches for known bugs
- **Tier 2** uses a multi-agent VLM workflow — a **Vision Analyst** (screenshots) and a **Physics Analyst** (telemetry/config) run in parallel, then a **Repair Synthesizer** cross-validates findings to output a safe JSON patch (config diffs only, no code generation)

Patches are gated by a **sandbox** (whitelist + value-range validation), the sim auto-reloads, and the system re-verifies all 10 invariants. If verification fails, GenieGuard runs a **self-reflection loop** to re-diagnose and retry.

Result: a closed-loop CI step that turns "physics hallucinations" into a deterministic, repeatable QA + repair workflow for game developers.

---

## Live Dashboard Demo

Open `web/dashboard.html` in a browser and press **"Start Auto Demo"**.

The dashboard features a **JP/EN language toggle** for international demos.

### Demo Flow

```
Act 1: Known Bug → Tier 1 Catalog Repair
Act 2: Unknown Bug → Tier 2 Multi-Agent VLM Reasoning + Self-Reflection
```

### Free Mode — Judge Challenge

Manually adjust any physics parameter via sliders and challenge GenieGuard to repair it with pure AI reasoning (no pre-defined patches).

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
Click "Random Break" → "Run GenieGuard"

**Option B: CLI**
```bash
# Random break
python break.py

# Run GenieGuard (auto detect → repair → verify)
python genieguard.py --no-break

# Or full pipeline (break → detect → repair → verify)
python genieguard.py
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    GenieGuard Pipeline                   │
├──────────┬──────────────────────────────────────────────┤
│  STEP 1  │  Inject Bug (Tier1 known / Tier2 unknown)   │
├──────────┼──────────────────────────────────────────────┤
│  STEP 2  │  Collect Telemetry + Screenshots             │
│          │  ├─ Tier 1: Invariant Check → Catalog Patch  │
│          │  └─ Tier 2: 3-Agent VLM → Sandbox Patch      │
│          │       ├─ Agent 1: Vision Analyst (parallel)   │
│          │       ├─ Agent 2: Physics Analyst (parallel)  │
│          │       └─ Agent 3: Repair Synthesizer          │
├──────────┼──────────────────────────────────────────────┤
│  STEP 3  │  Re-verify all 10 invariants                 │
│          │  └─ Self-Reflection Loop if failed            │
└──────────┴──────────────────────────────────────────────┘
```

---

## Bug Types

### Tier 1 — Known Bugs (Catalog Repair)

**Physics Simulator:**

| ID | Bug | Mutation | Visible Effect |
|----|-----|----------|----------------|
| B1 | Gravity Inversion | gravityY = -1 | Ball floats up |
| B2 | Collision Disabled | collisionMask = 0 | Falls through floor |
| B3 | Abnormal Restitution | restitution = 5.0 | Accelerating bounces |
| B4 | Zero Friction | friction = 0 | Slides forever |
| B5 | Bounds Disabled | boundsEnabled = false | Disappears off-screen |

**STG Shooter:**

| ID | Bug | Mutation | Visible Effect |
|----|-----|----------|----------------|
| S1 | Bullet Freeze | bulletSpeed = 0 | Bullets don't move |
| S2 | Hitbox Gone | hitboxRadius = 0 | No collision detection |
| S3 | Fire Disabled | fireRate = 999 | Can't shoot |
| S4 | Player Freeze | playerSpeed = 0 | Can't move |
| S5 | Enemy Freeze | enemySpeed = 0 | Enemies stop |

### Tier 2 — Unknown Bugs (VLM Reasoning Repair)

| ID | Bug | Mutation | Detection Method |
|----|-----|----------|-----------------|
| U1/X1 | Time/Spawn anomaly | timeScale=0.01 / spawnInterval=2 | Behavioral analysis |
| U2/X2 | Lateral gravity/Slow bullets | gravityX=5 / bulletSpeed=0.3 | Telemetry drift |
| U3/X3 | Heavy ball/Fast enemies | ballMass=10000 / enemySpeed=15 | Physics anomaly |
| U4/X4 | Locked inertia/Giant hitbox | ballInertia=99999999 / hitboxRadius=300 | VLM observation |
| U5/X5 | Tiny ball/Bullet spam | ballRadius=3 / fireRate=1 | Multi-screenshot analysis |

---

## Project Structure

```
genieguard/
├── web/                        # Web simulators
│   ├── index.html              # Physics simulator (Matter.js)
│   ├── stg.html                # STG shooter game
│   ├── dashboard.html          # Demo dashboard (JP/EN)
│   ├── sim.js                  # Physics engine
│   ├── config.js               # Physics parameters (repair target)
│   ├── telemetry.js            # Telemetry system
│   └── hud.js                  # HUD overlay
│
├── genieguard/                 # Python modules
│   ├── random_breaker.py       # Random bug injection
│   ├── telemetry_collector.py  # Telemetry collection
│   ├── invariant_checker.py    # Numeric invariant checks
│   ├── patch_selector.py       # LLM patch selection
│   ├── patch_applier.py        # Patch application
│   └── evidence_exporter.py    # Evidence export
│
├── data/
│   └── patch_catalog.json      # Patch catalog
│
├── genieguard.py               # Main CLI
├── break.py                    # Break script
├── server.py                   # Dev server
└── requirements.txt            # Dependencies
```

## Design Principles

1. **Telemetry-driven detection** — PASS/FAIL is determined by numeric invariants, not VLM
2. **Patch catalog (Tier 1)** — LLM selects a patch_id only; no code generation
3. **Sandbox validation (Tier 2)** — AI-generated patches are gated by whitelist + range checks
4. **Self-Reflection** — Failed repairs trigger re-diagnosis with failure context
5. **Multi-game support** — Same pipeline works for physics sims and STG shooters

## CLI Options

```bash
# Full pipeline (break → detect → repair → verify)
python genieguard.py

# Skip break (test current state)
python genieguard.py --no-break

# Inject specific bugs
python genieguard.py --specific B1 B3

# Set bug count
python genieguard.py --bugs 2

# Headless mode
python genieguard.py --headless
```

## Environment Variables

```bash
# Gemini API key (optional — falls back without it)
export GEMINI_API_KEY=your_api_key
```

## License

MIT License
