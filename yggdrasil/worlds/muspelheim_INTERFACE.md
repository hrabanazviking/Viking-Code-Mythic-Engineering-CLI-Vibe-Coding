# muspelheim.py — INTERFACE.md

## Class: `Muspelheim`

Transformation & Fiery Critique.

Handles critique loops, retry transformations, evolutionary refinement,
backlash assessment, and sub-branch ignition.

### `simulate_critique(results)`
Analyze results for flaws and issues.

Returns list of identified issues.

### `retry_transform(original, mutation_type)`
Transform a failed result for retry.

Args:
    original: Original value/task
    mutation_type: Type of mutation (retry, alt, expand)
    
Returns:
    Transformed value

### `refine_results(results, selector)`
Refine results by selecting the best.

Args:
    results: List of candidate results
    selector: Optional function to score results
    
Returns:
    Best refined result

### `assess_backlash(risks)`
Assess potential backlash/risk using Monte Carlo simulation.

Args:
    risks: List of risk probabilities
    
Returns:
    Overall risk score

### `ignite_subbranches(parent_task, branch_count)`
Ignite new sub-branches from a parent task.

Args:
    parent_task: Parent task to branch from
    branch_count: Number of branches to create
    
Returns:
    List of sub-branch tasks

### `generate_new_nodes(issues, original_dag)`
Generate new DAG nodes to address issues.

Args:
    issues: List of identified issues
    original_dag: Original DAG structure
    
Returns:
    List of new nodes to add

### `should_continue_refinement(iteration, max_iterations, issues_count)`
Determine if refinement should continue.

Returns True if more iterations are warranted.

### `get_critique_summary()`
Get summary of critique history.

---
**Contract Version**: 1.0 | v8.0.0
