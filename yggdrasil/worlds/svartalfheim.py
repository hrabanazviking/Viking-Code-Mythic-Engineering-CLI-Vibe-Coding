"""
Svartalfheim - Forging & Tool Crafting
=====================================

Dark elves/dwarves—master smiths, innovation, deep customization.
Building the artifacts.
"""

import logging
import json
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class Svartalfheim:
    """
    Forging & Tool Crafting.
    
    Handles script forging, artifact assembly, behavior customization,
    innovation loops, and persistent forging registries.
    """
    
    SCRIPT_TEMPLATES = {
        "calculator": "result = {expression}\nprint(result)",
        "data_processor": "import json\ndata = json.loads('{data}')\nprocessed = {operation}\nprint(json.dumps(processed))",
        "validator": "assert {condition}, '{error_message}'",
    }
    
    def __init__(self, forge_log_path: str = None):
        self.forge_log_path = forge_log_path
        self._forge_registry: Dict[str, Dict] = {}
    
    def forge_script(self, template_name: str, **kwargs) -> str:
        """Forge a script from template."""
        template = self.SCRIPT_TEMPLATES.get(template_name, "{code}")
        
        try:
            script = template.format(**kwargs)
            self._register_artifact(f"script_{template_name}", script)
            return script
        except KeyError as e:
            logger.warning(f"Missing template parameter: {e}")
            return template
    
    def assemble_modules(self, modules: List[str], separator: str = "\n\n") -> str:
        """Assemble multiple code modules."""
        assembled = separator.join(modules)
        self._register_artifact("assembled_module", assembled)
        return assembled
    
    def customize_behavior(self, config: Dict) -> Dict:
        """Parse and apply behavior configuration."""
        customized = {}
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("$"):
                # Variable reference - leave as is
                customized[key] = value
            else:
                customized[key] = value
        return customized
    
    def innovate_variants(self, base_tool: str, variants: int = 3) -> List[str]:
        """Generate tool variants for innovation."""
        return [f"{base_tool}_v{i+1}" for i in range(variants)]
    
    def _register_artifact(self, name: str, artifact: Any):
        """Register an artifact in the forge registry."""
        self._forge_registry[name] = {
            "artifact": artifact,
            "type": type(artifact).__name__,
        }
        
        # Persist to log if available
        if self.forge_log_path:
            try:
                with open(self.forge_log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"name": name, "type": type(artifact).__name__}) + "\n")
            except Exception as e:
                logger.warning(f"Failed to log artifact: {e}")
    
    def get_artifact(self, name: str) -> Optional[Any]:
        """Retrieve a forged artifact."""
        entry = self._forge_registry.get(name)
        return entry.get("artifact") if entry else None
    
    def list_artifacts(self) -> List[str]:
        """List all forged artifacts."""
        return list(self._forge_registry.keys())
    
    def forge_inline_script(self, code: str) -> str:
        """Create an inline executable script."""
        # Add header comment
        return f"# Forged by Svartalfheim\n{code}"
