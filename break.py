#!/usr/bin/env python3
"""
GenieGuard: Random Break Script
Convenience script to randomly break the simulator config for demos

Usage:
  python break.py           # Random 1-3 bugs
  python break.py --bugs 2  # Exactly 2 bugs
  python break.py --specific B1 B3  # Specific bugs
  python break.py --restore # Restore healthy config
"""

import sys
from pathlib import Path

# Add genieguard to path
sys.path.insert(0, str(Path(__file__).parent))

from genieguard.random_breaker import RandomBreaker


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Randomly break simulator config for demo'
    )
    parser.add_argument('--bugs', type=int, help='Number of bugs to inject (1-3)')
    parser.add_argument('--specific', nargs='+', help='Specific bug IDs (B1-B5)')
    parser.add_argument('--restore', action='store_true', help='Restore healthy config')
    parser.add_argument('--config', default='web/config.js', help='Config file path')

    args = parser.parse_args()

    breaker = RandomBreaker(args.config, 'output')

    if args.restore:
        breaker.restore_healthy()
        print("\n Config restored to healthy state!")
    else:
        info = breaker.break_randomly(num_bugs=args.bugs, specific_bugs=args.specific)
        print(f"\n Bugs injected: {info['applied_bugs']}")
        print("\nRefresh the browser to see the broken simulator.")
        print("Run 'python genieguard.py --no-break' to test and repair.")


if __name__ == '__main__':
    main()
