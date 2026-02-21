"""
GenieGuard: Patch Applier Module
Applies patches from catalog to config.js
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import difflib


class PatchApplier:
    """
    Applies fixes from patch catalog to config.js.
    No code generation - only parameter value replacement.
    """

    def __init__(self, config_path: str, catalog_path: str = None, output_dir: str = None):
        self.config_path = Path(config_path)
        self.catalog_path = Path(catalog_path) if catalog_path else Path('data/patch_catalog.json')
        self.output_dir = Path(output_dir) if output_dir else Path('output')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.catalog = self._load_catalog()
        self.applied_patches = []

    def _load_catalog(self) -> List[Dict]:
        """Load patch catalog"""
        if self.catalog_path.exists():
            with open(self.catalog_path, 'r') as f:
                return json.load(f)
        return []

    def apply_patches(self, patch_ids: List[str]) -> Dict:
        """
        Apply patches by ID.

        Args:
            patch_ids: List of patch IDs to apply (e.g., ['FIX_B1', 'FIX_B3'])

        Returns:
            Dict with applied patches info and diff
        """
        # Read current config
        with open(self.config_path, 'r') as f:
            original_content = f.read()

        # Parse current values
        current_config = self._parse_config(original_content)

        # Get patches to apply
        patches = [p for p in self.catalog if p['id'] in patch_ids]

        if not patches:
            return {
                'success': False,
                'error': f'No patches found for IDs: {patch_ids}',
                'applied': []
            }

        # Apply each patch
        new_config = dict(current_config)
        for patch in patches:
            if 'params' in patch:
                # Multiple parameters (e.g., FIX_B4)
                new_config.update(patch['params'])
            else:
                # Single parameter
                new_config[patch['param']] = patch['fix_value']

        # Write new config
        new_content = self._generate_config(new_config)
        with open(self.config_path, 'w') as f:
            f.write(new_content)

        # Generate diff
        diff = self._generate_diff(original_content, new_content)

        # Save diff
        diff_path = self.output_dir / 'patch.diff'
        with open(diff_path, 'w') as f:
            f.write(diff)

        self.applied_patches = patch_ids

        result = {
            'success': True,
            'applied': patch_ids,
            'patches': patches,
            'before': current_config,
            'after': new_config,
            'diff_path': str(diff_path),
            'diff': diff
        }

        print(f"[PATCH] Applied: {patch_ids}")
        return result

    def _parse_config(self, content: str) -> Dict:
        """Parse config values from config.js content"""
        config = {}

        # Match each parameter
        patterns = {
            'gravityY': r'gravityY:\s*(-?\d+(?:\.\d+)?)',
            'restitution': r'restitution:\s*(\d+(?:\.\d+)?)',
            'friction': r'friction:\s*(\d+(?:\.\d+)?)',
            'frictionAir': r'frictionAir:\s*(\d+(?:\.\d+)?)',
            'collisionMask': r'collisionMask:\s*(0x[A-Fa-f0-9]+|\d+)',
            'boundsEnabled': r'boundsEnabled:\s*(true|false)'
        }

        for param, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                value = match.group(1)
                # Convert to appropriate type
                if param == 'boundsEnabled':
                    config[param] = value == 'true'
                elif param == 'collisionMask':
                    config[param] = int(value, 16) if value.startswith('0x') else int(value)
                elif '.' in value:
                    config[param] = float(value)
                else:
                    config[param] = int(value)

        return config

    def _generate_config(self, config: Dict) -> str:
        """Generate config.js content from config dict"""

        def format_value(key, value):
            if isinstance(value, bool):
                return 'true' if value else 'false'
            elif key == 'collisionMask':
                if value == 0xFFFFFFFF or value == 4294967295:
                    return '0xFFFFFFFF'
                return str(value)
            else:
                return str(value)

        return '''// GenieGuard: World-Sim CI - Physics Configuration
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
            format_value('gravityY', config.get('gravityY', 1)),
            format_value('restitution', config.get('restitution', 0.6)),
            format_value('friction', config.get('friction', 0.1)),
            format_value('frictionAir', config.get('frictionAir', 0.01)),
            format_value('collisionMask', config.get('collisionMask', 0xFFFFFFFF)),
            format_value('boundsEnabled', config.get('boundsEnabled', True))
        )

    def _generate_diff(self, before: str, after: str) -> str:
        """Generate unified diff"""
        before_lines = before.splitlines(keepends=True)
        after_lines = after.splitlines(keepends=True)

        diff = difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile='config.js (before)',
            tofile='config.js (after)',
            lineterm=''
        )

        return ''.join(diff)

    def get_applied_patches(self) -> List[str]:
        """Get list of applied patch IDs"""
        return self.applied_patches


def test_applier():
    """Test the patch applier"""
    # Backup original config
    config_path = Path('web/config.js')
    if config_path.exists():
        backup = config_path.read_text()

    applier = PatchApplier('web/config.js', 'data/patch_catalog.json', 'output')

    # Apply patches
    result = applier.apply_patches(['FIX_B1', 'FIX_B3'])
    print("\nPatch Apply Result:")
    print(json.dumps({k: v for k, v in result.items() if k != 'diff'}, indent=2))
    print("\nDiff:")
    print(result['diff'])


if __name__ == '__main__':
    test_applier()
