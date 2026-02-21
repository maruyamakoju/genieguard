"""
GenieGuard: Evidence Exporter Module
Exports audit reports, diffs, screenshots, and CI results
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class EvidenceExporter:
    """
    Exports all evidence from the CI run:
    - audit_report.json
    - patch.diff
    - before.png / after.png
    - ci_result.txt
    - run_log.txt
    """

    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir) if output_dir else Path('output')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_entries = []

    def log(self, message: str, level: str = 'INFO'):
        """Add log entry"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }
        self.log_entries.append(entry)
        print(f"[{level}] {message}")

    def export_audit_report(
        self,
        scenario: str,
        result: str,
        bugs_detected: List[Dict],
        applied_patches: List[str],
        telemetry_before: Dict,
        telemetry_after: Dict,
        invariant_results_before: Dict,
        invariant_results_after: Dict
    ) -> str:
        """
        Export comprehensive audit report.

        Returns:
            Path to saved report
        """
        report = {
            'run_id': self.run_id,
            'scenario': scenario,
            'result': result,
            'timestamp': datetime.now().isoformat(),
            'bugs_detected': bugs_detected,
            'applied_patches': applied_patches,
            'telemetry_before': telemetry_before,
            'telemetry_after': telemetry_after,
            'invariant_results_before': invariant_results_before,
            'invariant_results_after': invariant_results_after,
            'evidence': {
                'before': 'before.png',
                'after': 'after.png',
                'diff': 'patch.diff'
            },
            'summary': self._generate_summary(bugs_detected, applied_patches, result)
        }

        path = self.output_dir / 'audit_report.json'
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.log(f"Audit report saved: {path}")
        return str(path)

    def _generate_summary(self, bugs: List[Dict], patches: List[str], result: str) -> str:
        """Generate human-readable summary"""
        if result == 'PASS':
            if not bugs:
                return "No bugs detected. Simulation is healthy."
            else:
                bug_ids = [b.get('id', 'Unknown') for b in bugs]
                return f"Detected and fixed {len(bugs)} bug(s): {', '.join(bug_ids)}. All invariants now pass."
        else:
            return f"Partial fix. Some invariants still failing."

    def export_ci_result(
        self,
        passed: bool,
        total_checks: int,
        passed_checks: int,
        details: Dict = None
    ) -> str:
        """
        Export CI result file.

        Returns:
            Path to saved result
        """
        if passed:
            status = 'PASS'
            icon = '  '
        else:
            status = 'FAIL'
            icon = '  '

        content = f"""{icon} GenieGuard CI Result: {status}
{'=' * 50}

Run ID: {self.run_id}
Timestamp: {datetime.now().isoformat()}

Invariant Checks: {passed_checks}/{total_checks} PASSED

"""
        if details:
            content += "Details:\n"
            for bug_id, info in details.items():
                status_str = info.get('status', 'UNKNOWN')
                reason = info.get('reason', '')
                icon = '' if status_str == 'PASS' else ''
                content += f"  {icon} {bug_id}: {status_str} - {reason}\n"

        content += f"\n{'=' * 50}\n"

        if passed:
            content += "All physics invariants verified. Simulator is safe to ship.\n"
        else:
            content += "Some invariants failed. Manual review recommended.\n"

        path = self.output_dir / 'ci_result.txt'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        self.log(f"CI result saved: {path}")
        return str(path)

    def export_run_log(self) -> str:
        """Export full run log"""
        content = "GenieGuard Run Log\n"
        content += "=" * 50 + "\n"
        content += f"Run ID: {self.run_id}\n"
        content += "=" * 50 + "\n\n"

        for entry in self.log_entries:
            content += f"[{entry['timestamp']}] [{entry['level']}] {entry['message']}\n"

        path = self.output_dir / 'run_log.txt'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return str(path)

    def save_screenshot(self, screenshot_bytes: bytes, name: str) -> str:
        """
        Save screenshot.

        Args:
            screenshot_bytes: PNG image data
            name: Filename (e.g., 'before.png')

        Returns:
            Path to saved screenshot
        """
        path = self.output_dir / name
        with open(path, 'wb') as f:
            f.write(screenshot_bytes)

        self.log(f"Screenshot saved: {path}")
        return str(path)

    def copy_diff(self, diff_content: str) -> str:
        """Save diff file"""
        path = self.output_dir / 'patch.diff'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(diff_content)

        self.log(f"Diff saved: {path}")
        return str(path)

    def get_output_dir(self) -> Path:
        """Get output directory path"""
        return self.output_dir

    def get_run_id(self) -> str:
        """Get current run ID"""
        return self.run_id


def test_exporter():
    """Test the evidence exporter"""
    exporter = EvidenceExporter('output')

    exporter.log("Starting test run")
    exporter.log("Breaking config", "INFO")
    exporter.log("Collecting telemetry", "INFO")
    exporter.log("Checking invariants", "INFO")
    exporter.log("B1 FAIL: Gravity inverted", "WARN")
    exporter.log("B3 FAIL: Restitution > 1", "WARN")
    exporter.log("Selecting patches", "INFO")
    exporter.log("Applying FIX_B1, FIX_B3", "INFO")
    exporter.log("Re-verifying", "INFO")
    exporter.log("All invariants pass", "INFO")

    # Export audit report
    exporter.export_audit_report(
        scenario='drop_ball',
        result='PASS',
        bugs_detected=[
            {'id': 'B1', 'rule': 'gravity_sign', 'status': 'FAIL->FIXED'},
            {'id': 'B3', 'rule': 'restitution_bound', 'status': 'FAIL->FIXED'}
        ],
        applied_patches=['FIX_B1', 'FIX_B3'],
        telemetry_before={'gravityY': -1, 'restitution': 5.0},
        telemetry_after={'gravityY': 1, 'restitution': 0.6},
        invariant_results_before={'B1': 'FAIL', 'B2': 'PASS', 'B3': 'FAIL', 'B4': 'PASS', 'B5': 'PASS'},
        invariant_results_after={'B1': 'PASS', 'B2': 'PASS', 'B3': 'PASS', 'B4': 'PASS', 'B5': 'PASS'}
    )

    # Export CI result
    exporter.export_ci_result(
        passed=True,
        total_checks=5,
        passed_checks=5,
        details={
            'B1': {'status': 'PASS', 'reason': 'Gravity normal'},
            'B2': {'status': 'PASS', 'reason': 'Collision enabled'},
            'B3': {'status': 'PASS', 'reason': 'Restitution normal'},
            'B4': {'status': 'PASS', 'reason': 'Friction present'},
            'B5': {'status': 'PASS', 'reason': 'Bounds enabled'}
        }
    )

    # Export run log
    exporter.export_run_log()

    print("\nTest export complete!")


if __name__ == '__main__':
    test_exporter()
