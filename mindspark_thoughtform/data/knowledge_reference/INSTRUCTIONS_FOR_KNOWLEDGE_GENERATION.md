# Instructions for Future Agents: Knowledge Base Generation

## The Golden Rule: REAL CONTENT ONLY
**NEVER use automated placeholders to reach a line count.** Every entry in Sigrid's knowledge base must be a high-quality, substantive piece of information infused with her unique Norse persona.

## Quality Standards

### 1. Persona Infusion (Skaldic Style)
- Every entry should reflect Sigrid’s voice: knowledgeable, slightly archaic, and framed through Norse mythology/tradition.
- **Example (Bad)**: "42. Gradient Descent: An optimization algorithm used to minimize a function."
- **Example (Good)**: "42. Gradient Descent (The Descent into the Valley of Truth): An optimization algorithm used to minimize a function by iteratively moving in the direction of steepest descent, as if a scout were navigating the treacherous slopes of the Ironwood."

### 2. Information Uniqueness
- Do not repeat definitions or structures between entries.
- Avoid using "The Continued Whispers" or "The Continued Breath" or any recursive placeholder language.

### 3. Metric-Driven Expansion vs. Quality
- While the target is 5000 entries, **quality takes absolute precedence**.
- It is better to have 500 real entries than 5000 "concepts."

## Process for High-Volume Expansion
When tasked with generating hundreds or thousands of entries:
1. **Batching**: Generate content in batches of no more than 100 entries.
2. **Verification**: Manually (or via specialized subagent) audit each batch for placeholder strings (`Concept`, `Continued Whispers`, etc.).
3. **Commit often**: Commit after every 100-200 real entries.

## How to Handle Existing Debt
If you encounter a file with "Ghost" entries (see [KNOWLEDGE_BASE_AUDIT_REPORT.md](file:///C:/Users/volma/.gemini/antigravity/brain/f7a00ceb-4a73-4cde-a610-47cf79c3d72f/KNOWLEDGE_BASE_AUDIT_REPORT.md)):
1. Truncate the file at the last legitimate entry.
2. Reset the status in `DOMAIN_PROGRESS.md` to "In Progress".
3. Resume generation using these standards.
