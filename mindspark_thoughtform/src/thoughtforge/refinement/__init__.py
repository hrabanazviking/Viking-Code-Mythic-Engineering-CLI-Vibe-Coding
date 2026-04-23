"""
Refinement layer — fragment salvage and citation enforcement.

Multi-draft generation → fragment extraction → intelligent reassembly →
final citation integrity gate.
"""

from thoughtforge.refinement.enforcement import EnforcementGate, EnforcementResult
from thoughtforge.refinement.salvage import FragmentSalvage, SalvageResult

__all__ = [
    "FragmentSalvage",
    "SalvageResult",
    "EnforcementGate",
    "EnforcementResult",
]
