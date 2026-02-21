#!/usr/bin/env python3
"""
GenieGuard: World-Sim CI
AI-Generated Simulator Audit & Self-Repair Pipeline

Main CLI Entry Point
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add genieguard to path
sys.path.insert(0, str(Path(__file__).parent))

from genieguard.random_breaker import RandomBreaker
from genieguard.telemetry_collector import TelemetryCollector
from genieguard.invariant_checker import InvariantChecker
from genieguard.patch_selector import PatchSelector
from genieguard.patch_applier import PatchApplier
from genieguard.evidence_exporter import EvidenceExporter


class GenieGuard:
    """
    Main GenieGuard CI Pipeline.

    Flow:
    1. [Optional] Random Break - Inject bugs
    2. Scenario Run - Operate simulator, collect telemetry
    3. Invariant Check - Numeric PASS/FAIL judgment
    4. Patch Selection - LLM selects patch_id (or fallback)
    5. Patch Apply - Fix config.js
    6. Re-verify - Run same scenario, confirm PASS
    7. Export Evidence - Save all artifacts
    """

    def __init__(self, config_path: str = 'web/config.js', output_dir: str = 'output'):
        self.config_path = Path(config_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.breaker = RandomBreaker(str(self.config_path), str(self.output_dir))
        self.collector = TelemetryCollector(str(self.output_dir))
        self.checker = InvariantChecker()
        self.selector = PatchSelector('data/patch_catalog.json')
        self.applier = PatchApplier(str(self.config_path), 'data/patch_catalog.json', str(self.output_dir))
        self.exporter = EvidenceExporter(str(self.output_dir))

        # State
        self.page = None
        self.browser = None

    async def run_full_pipeline(
        self,
        break_first: bool = True,
        num_bugs: int = None,
        specific_bugs: list = None,
        headless: bool = False
    ) -> dict:
        """
        Run the complete CI pipeline.

        Args:
            break_first: Whether to inject bugs before testing
            num_bugs: Number of bugs to inject (1-3)
            specific_bugs: Specific bug IDs to inject
            headless: Run browser in headless mode

        Returns:
            Dict with full results
        """
        self.exporter.log("=" * 60)
        self.exporter.log("GenieGuard: World-Sim CI - Starting Pipeline")
        self.exporter.log("=" * 60)

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                # Launch browser
                self.exporter.log("Launching browser...")
                self.browser = await p.chromium.launch(headless=headless)
                self.page = await self.browser.new_page()

                # Phase 1: Break (if requested)
                if break_first:
                    self.exporter.log("-" * 40)
                    self.exporter.log("PHASE 1: RANDOM BREAK")
                    break_info = self.breaker.break_randomly(num_bugs, specific_bugs)
                    self.exporter.log(f"Applied bugs: {break_info['applied_bugs']}")
                else:
                    self.exporter.log("Skipping break phase - testing current state")
                    break_info = None

                # Navigate to simulator (use HTTP server for ES modules)
                sim_url = "http://localhost:1111/index.html"
                self.exporter.log(f"Navigating to: {sim_url}")
                await self.page.goto(sim_url)
                await self.page.wait_for_timeout(1000)

                # Setup telemetry collector
                await self.collector.setup(self.page)

                # Phase 2: Run scenario and collect telemetry (BEFORE)
                self.exporter.log("-" * 40)
                self.exporter.log("PHASE 2: SCENARIO RUN (BEFORE)")

                # Take before screenshot
                before_screenshot = await self.page.screenshot()
                self.exporter.save_screenshot(before_screenshot, 'before.png')

                # Spawn ball and collect telemetry
                await self._run_scenario()
                frames_before = await self.collector.collect_frames(num_frames=20, interval_ms=50)
                summary_before = self.collector.get_summary(frames_before)
                config_before = await self.collector.get_current_config()

                self.exporter.log(f"Collected {len(frames_before)} telemetry frames")
                self.exporter.log(f"Config: gravityY={config_before.get('gravityY')}, restitution={config_before.get('restitution')}")

                # Phase 3: Invariant Check (BEFORE)
                self.exporter.log("-" * 40)
                self.exporter.log("PHASE 3: INVARIANT CHECK (BEFORE)")

                results_before = self.checker.check_all(frames_before, config_before)
                print(self.checker.summary())

                failed_bugs = self.checker.get_failed_bugs()
                if not failed_bugs:
                    self.exporter.log("All invariants PASS - no repair needed!")
                    return await self._finalize_pass(summary_before, results_before)

                self.exporter.log(f"Failed invariants: {failed_bugs}", "WARN")

                # Phase 4: Patch Selection
                self.exporter.log("-" * 40)
                self.exporter.log("PHASE 4: PATCH SELECTION")

                selection = self.selector.select_patches(
                    self.checker.to_dict(),
                    summary_before
                )
                self.exporter.log(f"Diagnosis: {selection['diagnosis']}")
                self.exporter.log(f"Selected patches: {selection['selected_patches']}")

                if not selection['selected_patches']:
                    self.exporter.log("No patches selected - cannot repair", "ERROR")
                    return await self._finalize_fail(summary_before, results_before)

                # Phase 5: Apply Patches
                self.exporter.log("-" * 40)
                self.exporter.log("PHASE 5: APPLY PATCHES")

                apply_result = self.applier.apply_patches(selection['selected_patches'])
                if apply_result['success']:
                    self.exporter.log(f"Patches applied successfully")
                    self.exporter.copy_diff(apply_result['diff'])
                else:
                    self.exporter.log(f"Patch application failed: {apply_result.get('error')}", "ERROR")
                    return await self._finalize_fail(summary_before, results_before)

                # Phase 6: Re-verify
                self.exporter.log("-" * 40)
                self.exporter.log("PHASE 6: RE-VERIFY (AFTER)")

                # Reload page to pick up new config
                await self.page.reload()
                await self.page.wait_for_timeout(1000)

                # Reset collector
                self.collector.clear()
                await self.collector.setup(self.page)

                # Run scenario again
                await self._run_scenario()
                frames_after = await self.collector.collect_frames(num_frames=20, interval_ms=50)
                summary_after = self.collector.get_summary(frames_after)
                config_after = await self.collector.get_current_config()

                # Take after screenshot
                after_screenshot = await self.page.screenshot()
                self.exporter.save_screenshot(after_screenshot, 'after.png')

                # Check invariants again
                results_after = self.checker.check_all(frames_after, config_after)
                print(self.checker.summary())

                failed_after = self.checker.get_failed_bugs()

                if not failed_after:
                    self.exporter.log("All invariants now PASS!")
                    return await self._finalize_success(
                        break_info,
                        summary_before, summary_after,
                        results_before, results_after,
                        selection, apply_result
                    )
                else:
                    self.exporter.log(f"Some invariants still failing: {failed_after}", "WARN")
                    return await self._finalize_partial(
                        break_info,
                        summary_before, summary_after,
                        results_before, results_after,
                        selection, apply_result,
                        failed_after
                    )

        except Exception as e:
            self.exporter.log(f"Pipeline error: {e}", "ERROR")
            raise
        finally:
            if self.browser:
                await self.browser.close()
            self.exporter.export_run_log()

    async def _run_scenario(self):
        """Run the drop_ball scenario"""
        # Click Reset
        await self.page.click('#reset-btn')
        await self.page.wait_for_timeout(200)

        # Click Spawn Ball
        await self.page.click('#spawn-btn')
        await self.page.wait_for_timeout(500)

    async def _finalize_pass(self, summary, results):
        """Finalize when already passing"""
        self.exporter.export_ci_result(
            passed=True,
            total_checks=5,
            passed_checks=5,
            details=self._format_results(results)
        )
        self.exporter.export_audit_report(
            scenario='drop_ball',
            result='PASS',
            bugs_detected=[],
            applied_patches=[],
            telemetry_before=summary,
            telemetry_after=summary,
            invariant_results_before=self._format_results(results),
            invariant_results_after=self._format_results(results)
        )
        return {'result': 'PASS', 'bugs_fixed': 0}

    async def _finalize_fail(self, summary, results):
        """Finalize when repair failed"""
        failed = self.checker.get_failed_bugs()
        passed = 5 - len(failed)

        self.exporter.export_ci_result(
            passed=False,
            total_checks=5,
            passed_checks=passed,
            details=self._format_results(results)
        )
        return {'result': 'FAIL', 'bugs_fixed': 0, 'remaining': failed}

    async def _finalize_success(self, break_info, summary_before, summary_after,
                                 results_before, results_after, selection, apply_result):
        """Finalize successful repair"""
        bugs_detected = [
            {
                'id': bug_id,
                'rule': results_before[bug_id].rule_name,
                'status': 'FAIL->FIXED'
            }
            for bug_id in self.checker.get_failed_bugs()
        ] if break_info else []

        # Use results from before check for bugs detected
        if break_info:
            checker_before = InvariantChecker()
            # We need the failed bugs from before
            bugs_detected = [
                {
                    'id': bug_id,
                    'rule': 'physics_invariant',
                    'status': 'FAIL->FIXED'
                }
                for bug_id in break_info['applied_bugs']
            ]

        self.exporter.export_ci_result(
            passed=True,
            total_checks=5,
            passed_checks=5,
            details=self._format_results(results_after)
        )

        self.exporter.export_audit_report(
            scenario='drop_ball',
            result='PASS',
            bugs_detected=bugs_detected,
            applied_patches=selection['selected_patches'],
            telemetry_before=summary_before,
            telemetry_after=summary_after,
            invariant_results_before=self._format_results(results_before),
            invariant_results_after=self._format_results(results_after)
        )

        return {
            'result': 'PASS',
            'bugs_fixed': len(selection['selected_patches']),
            'patches': selection['selected_patches']
        }

    async def _finalize_partial(self, break_info, summary_before, summary_after,
                                  results_before, results_after, selection, apply_result, failed_after):
        """Finalize partial repair"""
        passed = 5 - len(failed_after)

        self.exporter.export_ci_result(
            passed=False,
            total_checks=5,
            passed_checks=passed,
            details=self._format_results(results_after)
        )

        self.exporter.export_audit_report(
            scenario='drop_ball',
            result=f'PARTIAL ({passed}/5)',
            bugs_detected=[],
            applied_patches=selection['selected_patches'],
            telemetry_before=summary_before,
            telemetry_after=summary_after,
            invariant_results_before=self._format_results(results_before),
            invariant_results_after=self._format_results(results_after)
        )

        return {
            'result': 'PARTIAL',
            'bugs_fixed': len(selection['selected_patches']),
            'remaining': failed_after
        }

    def _format_results(self, results):
        """Format InvariantResult dict for export"""
        formatted = {}
        for bug_id, result in results.items():
            if hasattr(result, 'status'):
                formatted[bug_id] = {
                    'status': result.status.value,
                    'reason': result.reason
                }
            else:
                formatted[bug_id] = result
        return formatted


async def main():
    parser = argparse.ArgumentParser(
        description='GenieGuard: World-Sim CI - AI Simulator Audit & Self-Repair'
    )
    parser.add_argument('--config', default='web/config.js', help='Path to config.js')
    parser.add_argument('--output', default='output', help='Output directory')
    parser.add_argument('--no-break', action='store_true', help='Skip random break phase')
    parser.add_argument('--bugs', type=int, help='Number of bugs to inject (1-3)')
    parser.add_argument('--specific', nargs='+', help='Specific bug IDs to inject')
    parser.add_argument('--headless', action='store_true', help='Run browser headless')

    args = parser.parse_args()

    guard = GenieGuard(args.config, args.output)

    result = await guard.run_full_pipeline(
        break_first=not args.no_break,
        num_bugs=args.bugs,
        specific_bugs=args.specific,
        headless=args.headless
    )

    print("\n" + "=" * 60)
    print("GENIEGUARD CI RESULT:", result['result'])
    print("=" * 60)

    return 0 if result['result'] == 'PASS' else 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
