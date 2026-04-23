"""
Niflheim - Preservation & Misty Verification
============================================

Ice and fog—slowing, concealing, eternal chill.
Testing truths in uncertainty.
"""

import logging
import re
import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class Niflheim:
    """
    Preservation & Misty Verification.
    
    Handles confidence scoring, state preservation, uncertainty modeling,
    verification traps, and validation checks.
    """
    
    def __init__(self):
        self._snapshots: Dict[str, Any] = {}
        self._verification_results: List[Dict] = []
    
    def score_confidence(self, data: Any, expected_type: type = None) -> float:
        """Score confidence in data validity."""
        score = 0.5  # Base score
        
        # Check for None
        if data is None:
            return 0.1
        
        # Check type if expected
        if expected_type and isinstance(data, expected_type):
            score += 0.2
        
        # Check for content
        if isinstance(data, (str, list, dict)):
            if len(data) > 0:
                score += 0.2
        
        # Check for common error patterns
        if isinstance(data, str):
            if "error" in data.lower():
                score -= 0.2
            if "success" in data.lower():
                score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def snapshot_state(self, state: Any, snapshot_id: str = None) -> str:
        """Preserve state in a snapshot."""
        import json
        from datetime import datetime
        
        snapshot_id = snapshot_id or hashlib.sha256(
            json.dumps(state, default=str).encode()
        ).hexdigest()[:8]
        
        self._snapshots[snapshot_id] = {
            "state": state,
            "timestamp": datetime.now().isoformat(),
        }
        
        return snapshot_id
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Any]:
        """Retrieve a state snapshot."""
        entry = self._snapshots.get(snapshot_id)
        return entry.get("state") if entry else None
    
    def apply_slowdown(self, delay_seconds: float = 0.1):
        """Apply verification delay (for rate limiting)."""
        time.sleep(delay_seconds)
    
    def model_uncertainty(self, base_probability: float, noise: float = 0.1) -> float:
        """Model uncertainty with random noise."""
        import random
        uncertainty = random.uniform(-noise, noise)
        return max(0.0, min(1.0, base_probability + uncertainty))
    
    def set_verification_trap(self, pattern: str, test_string: str) -> Tuple[bool, str]:
        """
        Set a verification trap using regex.
        
        Returns: (passed, message)
        """
        try:
            match = re.match(pattern, test_string)
            passed = match is not None
            return passed, "Pattern matched" if passed else "Pattern did not match"
        except re.error as e:
            return False, f"Invalid pattern: {e}"
    
    def verify_result(
        self,
        result: Any,
        checks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run multiple verification checks on a result.
        
        Args:
            result: Result to verify
            checks: List of check configs with 'type' and 'params'
            
        Returns:
            Verification summary
        """
        passed = 0
        failed = 0
        details = []
        
        for check in checks:
            check_type = check.get("type", "exists")
            params = check.get("params", {})
            
            if check_type == "exists":
                success = result is not None
            elif check_type == "not_empty":
                success = bool(result)
            elif check_type == "type":
                success = isinstance(result, params.get("expected_type", object))
            elif check_type == "contains":
                success = params.get("value") in str(result)
            elif check_type == "regex":
                success, _ = self.set_verification_trap(params.get("pattern", ""), str(result))
            else:
                success = True
            
            if success:
                passed += 1
            else:
                failed += 1
            
            details.append({
                "type": check_type,
                "passed": success,
            })
        
        summary = {
            "passed": passed,
            "failed": failed,
            "total": len(checks),
            "success_rate": passed / max(1, len(checks)),
            "all_passed": failed == 0,
            "details": details,
        }
        
        self._verification_results.append(summary)
        
        return summary
    
    def freeze_if_uncertain(self, confidence: float, threshold: float = 0.5) -> bool:
        """Check if processing should freeze due to uncertainty."""
        return confidence < threshold
    
    def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        if not self._verification_results:
            return {"total_verifications": 0}
        
        total_passed = sum(v["passed"] for v in self._verification_results)
        total_failed = sum(v["failed"] for v in self._verification_results)
        
        return {
            "total_verifications": len(self._verification_results),
            "total_passed": total_passed,
            "total_failed": total_failed,
            "overall_success_rate": total_passed / max(1, total_passed + total_failed),
        }
