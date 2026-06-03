# Private Knowledge

Mythic can read from external, read-only private knowledge sources to supplement its understanding of your domain.

## SQLite Knowledge Sources

You can configure Mythic to search pre-compiled SQLite databases. This is useful for proprietary API documentation, internal engineering guidelines, or massive research compendiums.

## Configuration

Set the `MYTHIC_KNOWLEDGE_SQLITE_PATH` environment variable or define `knowledge.sources` in your project configuration.

## Searching Knowledge

In the interactive shell, you can request knowledge lookups naturally:
> "Search my knowledge database for guidelines on Hermes memory."

Mythic will parse the query, retrieve matching excerpts from the SQLite database, and inject them into the active LLM context before answering your question.

For manual inspection, use:
- `/knowledge` in the interactive shell.
- `mythic admin knowledge search <query>` via the command line.\n