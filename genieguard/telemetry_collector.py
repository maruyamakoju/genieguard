"""
GenieGuard: Telemetry Collector Module
Collects telemetry data from the simulator via Playwright
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


class TelemetryCollector:
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir) if output_dir else Path('output')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.frames: List[Dict] = []
        self.page = None

    async def setup(self, page):
        """Setup collector with Playwright page"""
        self.page = page
        self.frames = []

    async def collect_frame(self) -> Dict:
        """Collect a single telemetry frame"""
        if not self.page:
            raise RuntimeError("Collector not setup. Call setup() first.")

        try:
            telemetry = await self.page.evaluate('() => window.__telemetry__')
            if telemetry:
                telemetry['collected_at'] = datetime.now().isoformat()
                self.frames.append(telemetry)
                return telemetry
        except Exception as e:
            print(f"[TELEMETRY] Error collecting frame: {e}")

        return {}

    async def collect_frames(self, num_frames: int = 10, interval_ms: int = 50) -> List[Dict]:
        """
        Collect multiple telemetry frames.

        Args:
            num_frames: Number of frames to collect
            interval_ms: Interval between frames in milliseconds

        Returns:
            List of telemetry frames
        """
        collected = []

        for i in range(num_frames):
            frame = await self.collect_frame()
            if frame:
                collected.append(frame)
            await asyncio.sleep(interval_ms / 1000)

        print(f"[TELEMETRY] Collected {len(collected)} frames")
        return collected

    async def get_current_config(self) -> Dict:
        """Get current config values from telemetry"""
        if not self.page:
            raise RuntimeError("Collector not setup. Call setup() first.")

        try:
            telemetry = await self.page.evaluate('() => window.__telemetry__')
            if telemetry and 'config' in telemetry:
                return telemetry['config']
        except Exception as e:
            print(f"[TELEMETRY] Error getting config: {e}")

        return {}

    def get_summary(self, frames: List[Dict] = None) -> Dict:
        """
        Generate summary of collected telemetry.

        Returns:
            Summary dict with averages and trends
        """
        data = frames if frames else self.frames

        if not data:
            return {}

        # Extract ball data
        ball_y = [f['ball']['y'] for f in data if 'ball' in f]
        ball_vy = [f['ball']['vy'] for f in data if 'ball' in f]
        ball_vx = [f['ball']['vx'] for f in data if 'ball' in f]

        # Calculate y deltas (movement direction)
        y_deltas = []
        for i in range(len(ball_y) - 1):
            y_deltas.append(ball_y[i + 1] - ball_y[i])

        # Get config from first frame
        config = data[0].get('config', {}) if data else {}

        # Total collisions
        collisions = max([f.get('collisions', 0) for f in data]) if data else 0

        # Detect bounce patterns (for B3 detection)
        bounce_heights = self._detect_bounces(ball_y, ball_vy)

        summary = {
            'frame_count': len(data),
            'gravityY': config.get('gravityY', 1),
            'restitution': config.get('restitution', 0.6),
            'friction': config.get('friction', 0.1),
            'frictionAir': config.get('frictionAir', 0.01),
            'collisionMask': config.get('collisionMask', 0xFFFFFFFF),
            'boundsEnabled': config.get('boundsEnabled', True),
            'y_start': ball_y[0] if ball_y else 0,
            'y_end': ball_y[-1] if ball_y else 0,
            'y_delta_mean': sum(y_deltas) / len(y_deltas) if y_deltas else 0,
            'vy_max': max(abs(v) for v in ball_vy) if ball_vy else 0,
            'vx_end': ball_vx[-1] if ball_vx else 0,
            'collisions': collisions,
            'bounce_heights': bounce_heights,
            'config': config
        }

        return summary

    def _detect_bounces(self, y_values: List[float], vy_values: List[float]) -> List[float]:
        """Detect bounce heights from y and vy data"""
        bounces = []
        prev_vy_sign = 0

        for i, vy in enumerate(vy_values):
            current_sign = 1 if vy > 0 else -1 if vy < 0 else 0

            # Detect bounce (velocity sign change from positive to negative)
            if prev_vy_sign > 0 and current_sign < 0 and i > 0:
                # Local maximum in y
                bounces.append(y_values[i])

            prev_vy_sign = current_sign

        return bounces

    def save(self, filename: str = 'telemetry.json') -> str:
        """Save collected frames to JSON file"""
        path = self.output_dir / filename
        with open(path, 'w') as f:
            json.dump({
                'frames': self.frames,
                'summary': self.get_summary(),
                'saved_at': datetime.now().isoformat()
            }, f, indent=2)

        print(f"[TELEMETRY] Saved to: {path}")
        return str(path)

    def clear(self):
        """Clear collected frames"""
        self.frames = []


async def test_collector():
    """Test the telemetry collector"""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # Navigate to simulator
        await page.goto('file:///C:/Users/mimz7/Desktop/0221a/web/index.html')
        await page.wait_for_timeout(1000)

        # Setup collector
        collector = TelemetryCollector('output')
        await collector.setup(page)

        # Click spawn button
        await page.click('#spawn-btn')
        await page.wait_for_timeout(100)

        # Collect frames
        frames = await collector.collect_frames(num_frames=20, interval_ms=50)

        # Get summary
        summary = collector.get_summary(frames)
        print("\nSummary:")
        print(json.dumps(summary, indent=2))

        # Save
        collector.save()

        await browser.close()


if __name__ == '__main__':
    asyncio.run(test_collector())
