"""
GenieGuard: LLM Patch Selector Module
Uses Gemini to select patch IDs from catalog (no code generation)
"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path

# Load .env file
from dotenv import load_dotenv
load_dotenv()


class PatchSelector:
    """
    LLM-based patch selector.
    The LLM only selects patch_id from a fixed catalog - no code generation.
    Includes fallback to direct mapping if LLM fails.
    """

    # Direct mapping fallback (B1 -> FIX_B1)
    FALLBACK_MAP = {
        'B1': 'FIX_B1',
        'B2': 'FIX_B2',
        'B3': 'FIX_B3',
        'B4': 'FIX_B4',
        'B5': 'FIX_B5'
    }

    def __init__(self, catalog_path: str = None, api_key: str = None):
        self.catalog_path = Path(catalog_path) if catalog_path else Path('data/patch_catalog.json')
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
        self.catalog = self._load_catalog()
        self.client = None
        self._init_client()

    def _load_catalog(self) -> List[Dict]:
        """Load patch catalog from JSON file"""
        if self.catalog_path.exists():
            with open(self.catalog_path, 'r') as f:
                return json.load(f)
        return []

    def _init_client(self):
        """Initialize Gemini client"""
        if not self.api_key:
            print("[PATCH_SELECTOR] Warning: No API key found. Will use fallback mapping.")
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel('gemini-2.0-flash')
            print("[PATCH_SELECTOR] Gemini client initialized")
        except ImportError:
            print("[PATCH_SELECTOR] google-generativeai not installed. Using fallback.")
        except Exception as e:
            print(f"[PATCH_SELECTOR] Error initializing Gemini: {e}")

    def select_patches(
        self,
        invariant_results: Dict,
        telemetry_summary: Dict,
        max_retries: int = 3
    ) -> Dict:
        """
        Select patches for failed invariants.

        Args:
            invariant_results: Dict of bug_id -> InvariantResult
            telemetry_summary: Summary of telemetry data
            max_retries: Number of LLM retries before fallback

        Returns:
            Dict with 'diagnosis' and 'selected_patches'
        """
        # Get failed bugs
        failed_bugs = [
            bug_id for bug_id, result in invariant_results.items()
            if result.get('status') == 'FAIL' or (hasattr(result, 'status') and result.status.value == 'FAIL')
        ]

        if not failed_bugs:
            return {
                'diagnosis': 'No bugs detected - all invariants passed',
                'selected_patches': []
            }

        # Try LLM selection
        if self.client:
            for attempt in range(max_retries):
                try:
                    result = self._llm_select(invariant_results, telemetry_summary)
                    if result and 'selected_patches' in result:
                        print(f"[PATCH_SELECTOR] LLM selected: {result['selected_patches']}")
                        return result
                except Exception as e:
                    print(f"[PATCH_SELECTOR] LLM attempt {attempt + 1} failed: {e}")

        # Fallback: direct mapping
        print("[PATCH_SELECTOR] Using fallback mapping")
        return self._fallback_select(failed_bugs)

    def _llm_select(self, invariant_results: Dict, telemetry_summary: Dict) -> Dict:
        """Use LLM to select patches"""
        # Prepare available patches for prompt
        available_patches = [
            {'id': p['id'], 'desc': p['desc']}
            for p in self.catalog
        ]

        # Format invariant results
        formatted_results = {}
        for bug_id, result in invariant_results.items():
            if hasattr(result, 'status'):
                formatted_results[bug_id] = result.status.value
            else:
                formatted_results[bug_id] = result.get('status', 'UNKNOWN')

        prompt = f"""You are a physics simulator CI agent.
Given the invariant check results and telemetry summary,
select the correct patches from the catalog.

Input:
{{
  "invariant_results": {json.dumps(formatted_results)},
  "telemetry_summary": {{
    "gravityY": {telemetry_summary.get('gravityY', 1)},
    "y_delta_mean": {telemetry_summary.get('y_delta_mean', 0)},
    "restitution": {telemetry_summary.get('restitution', 0.6)},
    "friction": {telemetry_summary.get('friction', 0.1)},
    "frictionAir": {telemetry_summary.get('frictionAir', 0.01)},
    "collisionMask": {telemetry_summary.get('collisionMask', 0xFFFFFFFF)},
    "boundsEnabled": {str(telemetry_summary.get('boundsEnabled', True)).lower()},
    "collisions": {telemetry_summary.get('collisions', 0)}
  }},
  "available_patches": {json.dumps(available_patches)}
}}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "diagnosis": "string (1-2 sentences describing the bugs)",
  "selected_patches": ["FIX_B1", "FIX_B3"]
}}"""

        response = self.client.generate_content(prompt)
        text = response.text.strip()

        # Clean up response (remove markdown code blocks if present)
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        text = text.strip()

        return json.loads(text)

    def _fallback_select(self, failed_bugs: List[str]) -> Dict:
        """Fallback: directly map failed bugs to patches"""
        selected = [self.FALLBACK_MAP[bug] for bug in failed_bugs if bug in self.FALLBACK_MAP]

        return {
            'diagnosis': f"Detected bugs: {', '.join(failed_bugs)}. Using fallback mapping.",
            'selected_patches': selected
        }

    def get_patch_details(self, patch_ids: List[str]) -> List[Dict]:
        """Get full patch details from catalog"""
        return [p for p in self.catalog if p['id'] in patch_ids]


def test_selector():
    """Test the patch selector with mock data"""
    selector = PatchSelector()

    # Mock invariant results
    mock_results = {
        'B1': {'status': 'FAIL', 'reason': 'Gravity inverted'},
        'B2': {'status': 'PASS', 'reason': 'OK'},
        'B3': {'status': 'FAIL', 'reason': 'Restitution > 1'},
        'B4': {'status': 'PASS', 'reason': 'OK'},
        'B5': {'status': 'PASS', 'reason': 'OK'}
    }

    # Mock telemetry
    mock_telemetry = {
        'gravityY': -1,
        'restitution': 5.0,
        'friction': 0.1,
        'collisions': 0
    }

    result = selector.select_patches(mock_results, mock_telemetry)
    print("\nPatch Selection Result:")
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    test_selector()
