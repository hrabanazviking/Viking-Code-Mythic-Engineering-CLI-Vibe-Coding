"""
Cognition layer — scaffolds, intent routing, and the orchestration loop.

Deterministic YAML control objects steer any model toward grounded,
consistent, cite-verified responses.
"""

from thoughtforge.cognition.chat_history import ChatHistory, ChatMessage
from thoughtforge.cognition.core import ThoughtForgeCore
from thoughtforge.cognition.prompt_builder import PromptBuilder
from thoughtforge.cognition.router import InputRouter
from thoughtforge.cognition.scaffold import ScaffoldBuilder

__all__ = [
    "ChatHistory",
    "ChatMessage",
    "ThoughtForgeCore",
    "InputRouter",
    "ScaffoldBuilder",
    "PromptBuilder",
]
