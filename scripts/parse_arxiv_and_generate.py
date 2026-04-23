import json
import os
import sys
from pathlib import Path
import logging

# Add the parent directory to sys.path so we can import from the main project
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.openrouter import OpenRouterClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting arxiv AI theories integration report generation...")

    # Check for arxiv_results.json
    results_path = Path("arxiv_results.json")
    if not results_path.exists():
        logger.error("arxiv_results.json not found. Please run fetch_arxiv.py first.")
        sys.exit(1)

    with open(results_path, 'r', encoding='utf-8') as f:
        papers = json.load(f)

    logger.info(f"Loaded {len(papers)} papers from arxiv_results.json")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY environment variable not set.")
        sys.exit(1)

    client = OpenRouterClient(api_key=api_key)

    prompt = """
    You are an expert AI architect working on the Norse Saga Engine.
    I have fetched the latest AI and LLM theories from arXiv.
    Please read the following abstracts and generate a long full report on all theories,
    and individually detailed examples of how to integrate all the discovered methods
    into the Norse Saga Engine (cognitive architecture, memory, multi-agent interactions, etc.).

    Format the output as a Markdown data file.

    Papers:
    """

    for idx, paper in enumerate(papers):
        prompt += f"\n{idx+1}. Title: {paper.get('title')}\n   Summary: {paper.get('summary')}\n"

    messages = [
        {"role": "system", "content": "You are a helpful AI architect."},
        {"role": "user", "content": prompt}
    ]

    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": messages
    }

    logger.info("Generating report using OpenRouter API...")
    try:
        response = await client._request_with_retry(payload, model_name="google/gemini-2.5-flash") # Using a high quality model

        report_content = response.content

    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        sys.exit(1)

    out_dir = Path("data/txt_data_files")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "latest_ai_theories_integration_report_2025.md"

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    logger.info(f"Successfully generated and saved report to {out_path}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
