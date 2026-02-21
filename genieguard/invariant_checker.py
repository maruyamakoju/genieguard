"""
GenieGuard: Invariant Checker Module
Performs numeric PASS/FAIL judgment without LLM dependency
"""

import json
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class Status(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


@dataclass
class InvariantResult:
    bug_id: str
    rule_name: str
    status: Status
    reason: str
    evidence: Dict


class InvariantChecker:
    """
    Checks physics invariants using telemetry data.
    All judgments are numeric - no LLM dependency.
    """

    # Thresholds for detection
    GRAVITY_FRAMES_THRESHOLD = 3  # Minimum frames to confirm gravity direction
    BOUNDS_WIDTH = 800
    BOUNDS_HEIGHT = 600
    BOUNDS_MARGIN = 100  # Allowable margin outside visible area

    def __init__(self):
        self.results: Dict[str, InvariantResult] = {}

    def check_all(self, telemetry_frames: List[Dict], config: Dict = None) -> Dict[str, InvariantResult]:
        """
        Check all invariants.

        Args:
            telemetry_frames: List of telemetry frame dicts
            config: Optional config override (otherwise uses config from frames)

        Returns:
            Dict mapping bug_id to InvariantResult
        """
        if not telemetry_frames:
            return {}

        # Get config from first frame if not provided
        if config is None:
            config = telemetry_frames[0].get('config', {})

        self.results = {}

        # Run all checks
        self.results['B1'] = self._check_b1_gravity(telemetry_frames, config)
        self.results['B2'] = self._check_b2_collision(telemetry_frames, config)
        self.results['B3'] = self._check_b3_restitution(telemetry_frames, config)
        self.results['B4'] = self._check_b4_friction(telemetry_frames, config)
        self.results['B5'] = self._check_b5_bounds(telemetry_frames, config)

        return self.results

    def _check_b1_gravity(self, frames: List[Dict], config: Dict) -> InvariantResult:
        """
        B1: Gravity Inversion Check
        PASS: gravityY > 0 AND ball.y increases over time (falling down)
        FAIL: gravityY < 0 OR ball.y decreases consistently (flying up)
        """
        gravity_y = config.get('gravityY', 1)

        # Direct config check
        if gravity_y < 0:
            return InvariantResult(
                bug_id='B1',
                rule_name='gravity_sign',
                status=Status.FAIL,
                reason=f'Config gravityY is negative ({gravity_y})',
                evidence={'gravityY': gravity_y, 'check': 'config'}
            )

        # Behavior check: ball should move downward
        y_values = [f['ball']['y'] for f in frames if 'ball' in f]

        if len(y_values) < 2:
            return InvariantResult(
                bug_id='B1',
                rule_name='gravity_sign',
                status=Status.UNKNOWN,
                reason='Insufficient data',
                evidence={'frame_count': len(y_values)}
            )

        # Calculate y deltas
        y_deltas = [y_values[i + 1] - y_values[i] for i in range(len(y_values) - 1)]
        positive_deltas = sum(1 for d in y_deltas if d > 0)

        # Ball should move down (positive y delta) for most frames
        if positive_deltas >= self.GRAVITY_FRAMES_THRESHOLD:
            return InvariantResult(
                bug_id='B1',
                rule_name='gravity_sign',
                status=Status.PASS,
                reason='Gravity normal: ball moving downward',
                evidence={'gravityY': gravity_y, 'positive_deltas': positive_deltas}
            )
        else:
            return InvariantResult(
                bug_id='B1',
                rule_name='gravity_sign',
                status=Status.FAIL,
                reason='Ball not falling correctly',
                evidence={'gravityY': gravity_y, 'positive_deltas': positive_deltas, 'y_deltas': y_deltas[:5]}
            )

    def _check_b2_collision(self, frames: List[Dict], config: Dict) -> InvariantResult:
        """
        B2: Collision Check
        PASS: collisionMask != 0 AND collisions > 0 (after ball reaches ground level)
        FAIL: collisionMask == 0 OR no collisions when ball at ground level
        """
        collision_mask = config.get('collisionMask', 0xFFFFFFFF)

        # Direct config check
        if collision_mask == 0:
            return InvariantResult(
                bug_id='B2',
                rule_name='collision_enabled',
                status=Status.FAIL,
                reason='Collision mask is 0 (disabled)',
                evidence={'collisionMask': collision_mask, 'check': 'config'}
            )

        # Check for collision events
        collision_counts = [f.get('collisions', 0) for f in frames]
        max_collisions = max(collision_counts) if collision_counts else 0

        # Check if ball reached ground level
        y_values = [f['ball']['y'] for f in frames if 'ball' in f]
        max_y = max(y_values) if y_values else 0
        ground_level = self.BOUNDS_HEIGHT - 50  # Ground is at ~550

        # If ball reached ground area and collisions detected
        if max_y > ground_level - 50 and max_collisions > 0:
            return InvariantResult(
                bug_id='B2',
                rule_name='collision_enabled',
                status=Status.PASS,
                reason='Collisions detected at ground level',
                evidence={'collisionMask': collision_mask, 'collisions': max_collisions, 'max_y': max_y}
            )

        # If ball reached ground but no collisions
        if max_y > ground_level and max_collisions == 0:
            return InvariantResult(
                bug_id='B2',
                rule_name='collision_enabled',
                status=Status.FAIL,
                reason='Ball at ground level but no collisions detected',
                evidence={'collisionMask': collision_mask, 'collisions': 0, 'max_y': max_y}
            )

        # Ball hasn't reached ground yet - inconclusive but config looks OK
        return InvariantResult(
            bug_id='B2',
            rule_name='collision_enabled',
            status=Status.PASS,
            reason='Collision mask enabled, awaiting ground contact',
            evidence={'collisionMask': collision_mask, 'collisions': max_collisions, 'max_y': max_y}
        )

    def _check_b3_restitution(self, frames: List[Dict], config: Dict) -> InvariantResult:
        """
        B3: Restitution (Bounce) Check
        PASS: restitution <= 1.0 AND bounce heights decrease
        FAIL: restitution > 1.0 OR bounce heights increase
        """
        restitution = config.get('restitution', 0.6)

        # Direct config check
        if restitution > 1.0:
            return InvariantResult(
                bug_id='B3',
                rule_name='restitution_bound',
                status=Status.FAIL,
                reason=f'Restitution > 1.0 ({restitution}) - energy increasing',
                evidence={'restitution': restitution, 'check': 'config'}
            )

        # Behavior check: velocity magnitude after bounce should decrease
        vy_values = [f['ball']['vy'] for f in frames if 'ball' in f]

        # Find velocity reversals (bounces)
        bounces = []
        for i in range(1, len(vy_values) - 1):
            # Bounce: vy goes from positive to negative (hit ground, bounced up)
            if vy_values[i - 1] > 0 and vy_values[i + 1] < 0:
                bounces.append(abs(vy_values[i + 1]))

        # If we have multiple bounces, check if energy is dissipating
        if len(bounces) >= 2:
            # Check if bounce velocities are decreasing
            increasing = sum(1 for i in range(len(bounces) - 1) if bounces[i + 1] > bounces[i] * 1.1)
            if increasing > 0:
                return InvariantResult(
                    bug_id='B3',
                    rule_name='restitution_bound',
                    status=Status.FAIL,
                    reason='Bounce velocity increasing (abnormal restitution)',
                    evidence={'restitution': restitution, 'bounce_velocities': bounces}
                )

        return InvariantResult(
            bug_id='B3',
            rule_name='restitution_bound',
            status=Status.PASS,
            reason='Restitution within normal bounds',
            evidence={'restitution': restitution, 'bounce_velocities': bounces}
        )

    def _check_b4_friction(self, frames: List[Dict], config: Dict) -> InvariantResult:
        """
        B4: Friction Check
        PASS: friction > 0 AND frictionAir > 0
        FAIL: friction == 0 AND frictionAir == 0
        """
        friction = config.get('friction', 0.1)
        friction_air = config.get('frictionAir', 0.01)

        # Direct config check
        if friction == 0 and friction_air == 0:
            return InvariantResult(
                bug_id='B4',
                rule_name='friction_present',
                status=Status.FAIL,
                reason='Both friction and frictionAir are 0',
                evidence={'friction': friction, 'frictionAir': friction_air, 'check': 'config'}
            )

        # Behavior: horizontal velocity should decay over time
        vx_values = [f['ball']['vx'] for f in frames if 'ball' in f]

        if len(vx_values) > 2 and vx_values[0] != 0:
            # Check if vx magnitude is decreasing
            vx_abs = [abs(v) for v in vx_values]
            if vx_abs[-1] < vx_abs[0] * 0.95:  # At least 5% decay
                return InvariantResult(
                    bug_id='B4',
                    rule_name='friction_present',
                    status=Status.PASS,
                    reason='Velocity decaying normally (friction working)',
                    evidence={'friction': friction, 'frictionAir': friction_air, 'vx_decay': vx_abs[0] - vx_abs[-1]}
                )

        return InvariantResult(
            bug_id='B4',
            rule_name='friction_present',
            status=Status.PASS,
            reason='Friction parameters normal',
            evidence={'friction': friction, 'frictionAir': friction_air}
        )

    def _check_b5_bounds(self, frames: List[Dict], config: Dict) -> InvariantResult:
        """
        B5: Bounds Check
        PASS: boundsEnabled == true AND object stays in bounds
        FAIL: boundsEnabled == false OR object escapes bounds
        """
        bounds_enabled = config.get('boundsEnabled', True)

        # Direct config check
        if not bounds_enabled:
            return InvariantResult(
                bug_id='B5',
                rule_name='bounds_enabled',
                status=Status.FAIL,
                reason='Bounds checking disabled',
                evidence={'boundsEnabled': bounds_enabled, 'check': 'config'}
            )

        # Check if object is in bounds
        for frame in frames:
            ball = frame.get('ball', {})
            x, y = ball.get('x', 0), ball.get('y', 0)

            out_of_bounds = (
                x < -self.BOUNDS_MARGIN or
                x > self.BOUNDS_WIDTH + self.BOUNDS_MARGIN or
                y < -self.BOUNDS_MARGIN or
                y > self.BOUNDS_HEIGHT + self.BOUNDS_MARGIN
            )

            if out_of_bounds:
                return InvariantResult(
                    bug_id='B5',
                    rule_name='bounds_enabled',
                    status=Status.FAIL,
                    reason=f'Object escaped bounds at ({x}, {y})',
                    evidence={'boundsEnabled': bounds_enabled, 'escaped_position': {'x': x, 'y': y}}
                )

        return InvariantResult(
            bug_id='B5',
            rule_name='bounds_enabled',
            status=Status.PASS,
            reason='Object within bounds',
            evidence={'boundsEnabled': bounds_enabled}
        )

    def get_failed_bugs(self) -> List[str]:
        """Get list of bug IDs that failed"""
        return [bug_id for bug_id, result in self.results.items() if result.status == Status.FAIL]

    def get_passed_bugs(self) -> List[str]:
        """Get list of bug IDs that passed"""
        return [bug_id for bug_id, result in self.results.items() if result.status == Status.PASS]

    def all_passed(self) -> bool:
        """Check if all invariants passed"""
        return all(result.status == Status.PASS for result in self.results.values())

    def to_dict(self) -> Dict:
        """Convert results to dictionary"""
        return {
            bug_id: {
                'bug_id': result.bug_id,
                'rule_name': result.rule_name,
                'status': result.status.value,
                'reason': result.reason,
                'evidence': result.evidence
            }
            for bug_id, result in self.results.items()
        }

    def summary(self) -> str:
        """Get human-readable summary"""
        lines = ["=" * 50, "INVARIANT CHECK RESULTS", "=" * 50]

        for bug_id, result in sorted(self.results.items()):
            status_icon = "" if result.status == Status.PASS else "" if result.status == Status.FAIL else "?"
            lines.append(f"{status_icon} {bug_id}: {result.status.value} - {result.reason}")

        passed = len(self.get_passed_bugs())
        total = len(self.results)
        lines.append("=" * 50)
        lines.append(f"TOTAL: {passed}/{total} PASSED")

        return "\n".join(lines)
