"""
Midgard - Manifestation & Final Weaving
=======================================

The realm of mortals—endurance, adaptation, grounding the cosmic
in the tangible. Where all converges.

Processes:
- Result compression and summarization
- Adaptive output weaving
- Completeness checks
- Human-readable formatting
- Final manifestation delivery

This is where the final response is assembled for the user.
"""

import logging
import json
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class WovenOutput:
    """A final assembled output from Midgard."""
    content: str
    format: str  # text, json, html, markdown
    sources: List[str]  # Source node IDs
    completeness: float  # 0-1 how complete is the response
    word_count: int
    timestamp: datetime = field(default_factory=datetime.now)


class Midgard:
    """
    Manifestation & Final Weaving.
    
    Handles:
    - Result compression through summarization
    - Adaptive weaving of outputs from memory dumps
    - Endurance checks for completeness
    - Human-readable formatting
    - Final manifestation delivery
    """
    
    # Format templates
    FORMATS = {
        "text": "{content}",
        "json": '{{"result": {content}}}',
        "markdown": "## Result\n\n{content}",
        "html": "<div class='result'>{content}</div>",
    }
    
    def __init__(self, llm_queue=None):
        """
        Initialize Midgard.
        
        Args:
            llm_queue: Optional LLM queue for summarization
        """
        self.llm_queue = llm_queue
        self._output_history: List[WovenOutput] = []
    
    def compress_results(self, results: Dict[str, Any], max_length: int = 1000) -> Dict[str, Any]:
        """
        Compress results by truncating long values.
        
        Args:
            results: Dictionary of results to compress
            max_length: Maximum length for string values
            
        Returns:
            Compressed results
        """
        compressed = {}
        
        for key, value in results.items():
            if isinstance(value, str) and len(value) > max_length:
                compressed[key] = value[:max_length] + "..."
            elif isinstance(value, dict):
                compressed[key] = self.compress_results(value, max_length)
            elif isinstance(value, list) and len(value) > 10:
                compressed[key] = value[:10] + ["..."]
            else:
                compressed[key] = value
        
        return compressed
    
    def merge_outputs(self, memory_dumps: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge outputs from multiple nodes into unified result.
        
        Args:
            memory_dumps: Results from different nodes
            
        Returns:
            Merged output
        """
        merged = {}
        
        for node_id, dump in memory_dumps.items():
            if isinstance(dump, dict):
                # Merge dict results
                for key, value in dump.items():
                    if key not in merged:
                        merged[key] = value
                    elif isinstance(merged[key], list) and isinstance(value, list):
                        merged[key].extend(value)
                    elif isinstance(merged[key], dict) and isinstance(value, dict):
                        merged[key].update(value)
                    else:
                        # Create list of multiple values
                        if not isinstance(merged[key], list):
                            merged[key] = [merged[key]]
                        merged[key].append(value)
            else:
                merged[node_id] = dump
        
        return merged
    
    def check_completeness(self, merged: Dict[str, Any], expected_keys: List[str] = None) -> Tuple[bool, float]:
        """
        Check if output is complete.
        
        Args:
            merged: Merged output dictionary
            expected_keys: Keys that should be present
            
        Returns:
            (is_complete, completeness_score)
        """
        if not merged:
            return False, 0.0
        
        # Check for empty values
        non_empty = sum(1 for v in merged.values() if v is not None and v != "" and v != [])
        total = len(merged)
        
        completeness = non_empty / max(1, total)
        
        # Check expected keys if provided
        if expected_keys:
            found = sum(1 for k in expected_keys if k in merged)
            key_completeness = found / len(expected_keys)
            completeness = (completeness + key_completeness) / 2
        
        return completeness >= 0.7, completeness
    
    def format_readable(self, content: Any, format_type: str = "text") -> str:
        """
        Format content for human readability.
        
        Args:
            content: Content to format
            format_type: Output format (text, json, markdown, html)
            
        Returns:
            Formatted string
        """
        # Convert to string if needed
        if isinstance(content, dict):
            content_str = json.dumps(content, indent=2, default=str)
        elif isinstance(content, list):
            content_str = "\n".join(str(item) for item in content)
        else:
            content_str = str(content)
        
        # Apply format template
        if format_type in self.FORMATS:
            template = self.FORMATS[format_type]
            if format_type == "json":
                # JSON needs special handling
                try:
                    parsed = json.loads(content_str) if isinstance(content_str, str) else content_str
                    return json.dumps({"result": parsed}, indent=2, default=str)
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    logger.warning("Midgard JSON formatting fallback triggered: %s", exc)
                    return json.dumps({"result": content_str}, indent=2)
            else:
                return template.format(content=content_str)
        
        return content_str
    
    def weave_narrative(self, results: Dict[str, Any], query: str = "") -> str:
        """
        Weave results into a narrative response.
        
        Args:
            results: Results to weave
            query: Original query for context
            
        Returns:
            Narrative text
        """
        parts = []
        
        if query:
            parts.append(f"Regarding: {query}\n")
        
        for key, value in results.items():
            if isinstance(value, dict):
                parts.append(f"\n{key.replace('_', ' ').title()}:")
                for k, v in value.items():
                    parts.append(f"  - {k}: {v}")
            elif isinstance(value, list):
                parts.append(f"\n{key.replace('_', ' ').title()}:")
                for item in value[:5]:  # Max 5 items
                    parts.append(f"  • {item}")
                if len(value) > 5:
                    parts.append(f"  ... and {len(value) - 5} more")
            else:
                parts.append(f"\n{key.replace('_', ' ').title()}: {value}")
        
        return "\n".join(parts)
    
    def deliver_manifestation(
        self,
        results: Dict[str, Any],
        query: str = "",
        format_type: str = "text"
    ) -> WovenOutput:
        """
        Create final deliverable output.
        
        Args:
            results: All results to assemble
            query: Original query
            format_type: Output format
            
        Returns:
            WovenOutput object
        """
        # Compress if needed
        compressed = self.compress_results(results)
        
        # Merge outputs
        merged = self.merge_outputs({"main": compressed})
        
        # Check completeness
        is_complete, completeness = self.check_completeness(merged)
        
        # Format
        if format_type == "narrative":
            content = self.weave_narrative(merged, query)
        else:
            content = self.format_readable(merged, format_type)
        
        # Create output
        output = WovenOutput(
            content=content,
            format=format_type,
            sources=list(results.keys()) if isinstance(results, dict) else ["unknown"],
            completeness=completeness,
            word_count=len(content.split()),
        )
        
        self._output_history.append(output)
        
        # Trim history
        if len(self._output_history) > 100:
            self._output_history = self._output_history[-50:]
        
        logger.info(f"Midgard delivered: {output.word_count} words, "
                   f"completeness={completeness:.2f}")
        
        return output
    
    def assemble_from_dag(
        self,
        dag_results: Dict[str, Any],
        query: str = "",
        format_type: str = "text"
    ) -> WovenOutput:
        """
        Assemble output from DAG execution results.
        
        Args:
            dag_results: Results from DAG execution
            query: Original query
            format_type: Output format
            
        Returns:
            WovenOutput object
        """
        # Filter for successful results
        successful = {
            k: v for k, v in dag_results.items()
            if v is not None and not (isinstance(v, dict) and v.get("error"))
        }
        
        if not successful:
            return WovenOutput(
                content="No successful results to assemble.",
                format=format_type,
                sources=[],
                completeness=0.0,
                word_count=5,
            )
        
        return self.deliver_manifestation(successful, query, format_type)
    
    def get_output_history(self, limit: int = 10) -> List[Dict]:
        """Get recent output summaries."""
        return [
            {
                "format": o.format,
                "word_count": o.word_count,
                "completeness": o.completeness,
                "sources": len(o.sources),
                "timestamp": o.timestamp.isoformat(),
            }
            for o in self._output_history[-limit:]
        ]
