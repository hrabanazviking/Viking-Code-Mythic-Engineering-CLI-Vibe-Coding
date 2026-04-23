# midgard.py — INTERFACE.md

## Class: `WovenOutput`

A final assembled output from Midgard.

## Class: `Midgard`

Manifestation & Final Weaving.

Handles:
- Result compression through summarization
- Adaptive weaving of outputs from memory dumps
- Endurance checks for completeness
- Human-readable formatting
- Final manifestation delivery

### `compress_results(results, max_length)`
Compress results by truncating long values.

Args:
    results: Dictionary of results to compress
    max_length: Maximum length for string values
    
Returns:
    Compressed results

### `merge_outputs(memory_dumps)`
Merge outputs from multiple nodes into unified result.

Args:
    memory_dumps: Results from different nodes
    
Returns:
    Merged output

### `check_completeness(merged, expected_keys)`
Check if output is complete.

Args:
    merged: Merged output dictionary
    expected_keys: Keys that should be present
    
Returns:
    (is_complete, completeness_score)

### `format_readable(content, format_type)`
Format content for human readability.

Args:
    content: Content to format
    format_type: Output format (text, json, markdown, html)
    
Returns:
    Formatted string

### `weave_narrative(results, query)`
Weave results into a narrative response.

Args:
    results: Results to weave
    query: Original query for context
    
Returns:
    Narrative text

### `deliver_manifestation(results, query, format_type)`
Create final deliverable output.

Args:
    results: All results to assemble
    query: Original query
    format_type: Output format
    
Returns:
    WovenOutput object

### `assemble_from_dag(dag_results, query, format_type)`
Assemble output from DAG execution results.

Args:
    dag_results: Results from DAG execution
    query: Original query
    format_type: Output format
    
Returns:
    WovenOutput object

### `get_output_history(limit)`
Get recent output summaries.

---
**Contract Version**: 1.0 | v8.0.0
