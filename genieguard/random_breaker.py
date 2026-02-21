"""
GenieGuard: Random Breaker Module
Randomly injects 1-3 bugs into the simulator config
"""

import random
import json
import re
from pathlib import Path
from datetime import datetime

# Bug definitions - each bug modifies specific config parameters
BUGS = {
    'B1': {'gravityY': -1},                          # Gravity inverted
    'B2': {'collisionMask': 0},                      # Collision disabled
    'B3': {'restitution': 5.0},                      # Abnormal bounce
    'B4': {'friction': 0, 'frictionAir': 0},         # No friction
    'B5': {'boundsEnabled': False},                  # Objects escape
}

# Healthy defaults
HEALTHY_CONFIG = {
    'gravityY': 1,
    'restitution': 0.6,
    'friction': 0.1,
    'frictionAir': 0.01,
    'collisionMask': 0xFFFFFFFF,
    'boundsEnabled': True
}


class RandomBreaker:
    def __init__(self, config_path: str, output_dir: str = None):
        self.config_path = Path(config_path)
        self.output_dir = Path(output_dir) if output_dir else Path('output')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.applied_bugs = []
        self.broken_config = {}

    def break_randomly(self, num_bugs: int = None, specific_bugs: list = None) -> dict:
        """
        Randomly break the config by injecting 1-3 bugs.

        Args:
            num_bugs: Specific number of bugs to inject (1-3)
            specific_bugs: List of specific bug IDs to apply

        Returns:
            Dictionary with break info
        """
        # Determine which bugs to apply
        if specific_bugs:
            selected = specific_bugs
        else:
            k = num_bugs if num_bugs else random.randint(1, 3)
            k = min(k, len(BUGS))
            selected = random.sample(list(BUGS.keys()), k=k)

        self.applied_bugs = selected

        # Start with healthy config
        self.broken_config = dict(HEALTHY_CONFIG)

        # Apply selected bugs
        for bug_id in selected:
            self.broken_config.update(BUGS[bug_id])

        # Write broken config to file
        self._write_config()

        # Log the break
        break_info = {
            'timestamp': datetime.now().isoformat(),
            'applied_bugs': selected,
            'broken_config': self.broken_config,
            'config_path': str(self.config_path)
        }

        # Save break log
        log_path = self.output_dir / 'break_log.json'
        with open(log_path, 'w') as f:
            json.dump(break_info, f, indent=2)

        print(f"[BREAK] Applied bugs: {selected}")
        print(f"[BREAK] Config written to: {self.config_path}")

        return break_info

    def restore_healthy(self) -> dict:
        """Restore config to healthy state"""
        self.broken_config = dict(HEALTHY_CONFIG)
        self.applied_bugs = []
        self._write_config()

        print("[BREAK] Config restored to healthy state")

        return {
            'timestamp': datetime.now().isoformat(),
            'config': HEALTHY_CONFIG,
            'config_path': str(self.config_path)
        }

    def _write_config(self):
        """Write current config to config.js file"""
        config = self.broken_config

        # Format values properly for JavaScript
        def format_value(key, value):
            if isinstance(value, bool):
                return 'true' if value else 'false'
            elif key == 'collisionMask':
                if value == 0xFFFFFFFF or value == 4294967295:
                    return '0xFFFFFFFF'
                return str(value)
            else:
                return str(value)

        config_js = '''// GenieGuard: World-Sim CI - Physics Configuration
// This file is the repair target (whitelist)

export const SIM_CONFIG = {
  gravityY: %s,              // B1: -1 when broken (gravity inverted)
  restitution: %s,         // B3: 5.0 when broken (abnormal bounce)
  friction: %s,            // B4: 0 when broken (no friction)
  frictionAir: %s,        // B4: 0 when broken (no air friction)
  collisionMask: %s, // B2: 0 when broken (collision disabled)
  boundsEnabled: %s        // B5: false when broken (objects escape)
};

// Healthy defaults for reference
export const HEALTHY_CONFIG = {
  gravityY: 1,
  restitution: 0.6,
  friction: 0.1,
  frictionAir: 0.01,
  collisionMask: 0xFFFFFFFF,
  boundsEnabled: true
};
''' % (
            format_value('gravityY', config['gravityY']),
            format_value('restitution', config['restitution']),
            format_value('friction', config['friction']),
            format_value('frictionAir', config['frictionAir']),
            format_value('collisionMask', config['collisionMask']),
            format_value('boundsEnabled', config['boundsEnabled'])
        )

        with open(self.config_path, 'w') as f:
            f.write(config_js)

    def get_applied_bugs(self) -> list:
        """Get list of currently applied bug IDs"""
        return self.applied_bugs

    def get_broken_config(self) -> dict:
        """Get current broken config"""
        return self.broken_config


def main():
    """CLI entry point for breaking config"""
    import argparse

    parser = argparse.ArgumentParser(description='Randomly break simulator config')
    parser.add_argument('--config', default='web/config.js', help='Path to config.js')
    parser.add_argument('--output', default='output', help='Output directory')
    parser.add_argument('--bugs', type=int, help='Number of bugs to inject (1-3)')
    parser.add_argument('--specific', nargs='+', help='Specific bug IDs to apply')
    parser.add_argument('--restore', action='store_true', help='Restore healthy config')

    args = parser.parse_args()

    breaker = RandomBreaker(args.config, args.output)

    if args.restore:
        breaker.restore_healthy()
    else:
        breaker.break_randomly(num_bugs=args.bugs, specific_bugs=args.specific)


if __name__ == '__main__':
    main()
