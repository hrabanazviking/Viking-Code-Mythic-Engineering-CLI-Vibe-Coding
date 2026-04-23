"""
forge_memory.py — CLI for building and managing the ThoughtForge knowledge database.

Usage:
  python forge_memory.py init
  python forge_memory.py wikidata --dump /path/to/latest-all.json.gz
  python forge_memory.py conceptnet --csv /path/to/conceptnet-assertions-5.7.0.csv.gz
  python forge_memory.py geonames --txt /path/to/allCountries.txt
  python forge_memory.py dbpedia --json /path/to/dbpedia-abstracts.jsonl
  python forge_memory.py reference
  python forge_memory.py embeddings
  python forge_memory.py status
  python forge_memory.py all --wikidata-dump /path/to/dump.json.gz
"""

import logging
import sys
from pathlib import Path

import click

from thoughtforge.etl.embeddings import build_entity_embeddings, build_reference_embeddings
from thoughtforge.etl.schema import get_entity_count, initialize_schema, rebuild_fts_indexes
from thoughtforge.etl.sources import ConceptNetETL, DBpediaETL, GeoNamesETL, ReferenceDataETL
from thoughtforge.etl.wikidata import WikidataETL
from thoughtforge.utils.config import load_config
from thoughtforge.utils.logging_setup import setup_logging
from thoughtforge.utils.paths import get_knowledge_db_path

# Bootstrap logging before any Click commands run
setup_logging(load_config())
logger = logging.getLogger("forge_memory")


@click.group()
@click.option("--db", default=None, help="Path to knowledge.db (default: auto-resolved)")
@click.pass_context
def cli(ctx: click.Context, db: str | None) -> None:
    """ThoughtForge Memory Forge — sovereign offline knowledge database builder."""
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = Path(db) if db else get_knowledge_db_path()


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize the knowledge database schema (idempotent)."""
    db_path: Path = ctx.obj["db_path"]
    click.echo(f"Initializing schema at: {db_path}")
    initialize_schema(db_path)
    click.echo("Schema initialized successfully.")


@cli.command()
@click.option("--dump", required=True, type=click.Path(exists=True), help="Path to latest-all.json.gz")
@click.option("--limit", default=None, type=int, help="Stop after N entities (for testing)")
@click.option("--batch-size", default=2000, show_default=True, help="Insert batch size")
@click.option("--languages", default="en", show_default=True, help="Comma-separated language codes")
@click.pass_context
def wikidata(ctx: click.Context, dump: str, limit: int | None, batch_size: int, languages: str) -> None:
    """Stream the full Wikidata dump into the knowledge database."""
    db_path: Path = ctx.obj["db_path"]
    langs = [l.strip() for l in languages.split(",")]
    click.echo(f"Starting Wikidata ETL from: {dump}")
    click.echo(f"Target DB: {db_path}")
    click.echo(f"Languages: {langs}")
    if limit:
        click.echo(f"Limit: {limit:,} entities (test mode)")

    etl = WikidataETL(db_path)
    stats = etl.build(
        dump_path=dump,
        batch_size=batch_size,
        limit=limit,
        languages=langs,
    )
    click.echo(f"\nWikidata ETL complete:")
    for k, v in stats.items():
        click.echo(f"  {k}: {v:,}")


@cli.command()
@click.option("--csv", required=True, type=click.Path(exists=True), help="Path to conceptnet CSV or CSV.gz")
@click.option("--limit", default=None, type=int)
@click.option("--languages", default="en", show_default=True)
@click.pass_context
def conceptnet(ctx: click.Context, csv: str, limit: int | None, languages: str) -> None:
    """Ingest ConceptNet 5 commonsense assertions."""
    db_path: Path = ctx.obj["db_path"]
    langs = [l.strip() for l in languages.split(",")]
    click.echo(f"Starting ConceptNet ETL from: {csv}")

    etl = ConceptNetETL(db_path)
    stats = etl.build(csv_path=csv, languages=langs, limit=limit)
    click.echo(f"\nConceptNet ETL complete:")
    for k, v in stats.items():
        click.echo(f"  {k}: {v:,}")


@cli.command()
@click.option("--txt", required=True, type=click.Path(exists=True), help="Path to allCountries.txt")
@click.option("--min-population", default=0, show_default=True)
@click.option("--limit", default=None, type=int)
@click.pass_context
def geonames(ctx: click.Context, txt: str, min_population: int, limit: int | None) -> None:
    """Ingest GeoNames geographic entities."""
    db_path: Path = ctx.obj["db_path"]
    click.echo(f"Starting GeoNames ETL from: {txt}")

    etl = GeoNamesETL(db_path)
    stats = etl.build(txt_path=txt, min_population=min_population, limit=limit)
    click.echo(f"\nGeoNames ETL complete:")
    for k, v in stats.items():
        click.echo(f"  {k}: {v:,}")


@cli.command()
@click.option("--json", "json_path", required=True, type=click.Path(exists=True))
@click.option("--limit", default=None, type=int)
@click.pass_context
def dbpedia(ctx: click.Context, json_path: str, limit: int | None) -> None:
    """Ingest DBpedia entity abstracts."""
    db_path: Path = ctx.obj["db_path"]
    click.echo(f"Starting DBpedia ETL from: {json_path}")

    etl = DBpediaETL(db_path)
    stats = etl.build(json_path=json_path, limit=limit)
    click.echo(f"\nDBpedia ETL complete:")
    for k, v in stats.items():
        click.echo(f"  {k}: {v:,}")


@cli.command()
@click.option("--ref-dir", default=None, type=click.Path(), help="Override reference data directory")
@click.pass_context
def reference(ctx: click.Context, ref_dir: str | None) -> None:
    """Ingest all built-in knowledge reference documents."""
    db_path: Path = ctx.obj["db_path"]
    ref_path = Path(ref_dir) if ref_dir else None
    click.echo("Starting reference data ingestion...")

    etl = ReferenceDataETL(db_path)
    stats = etl.build(ref_dir=ref_path)
    click.echo(f"\nReference ETL complete:")
    for k, v in stats.items():
        click.echo(f"  {k}: {v:,}")


@cli.command()
@click.option("--model", default="all-MiniLM-L6-v2", show_default=True)
@click.option("--batch-size", default=128, show_default=True)
@click.option("--limit", default=None, type=int)
@click.pass_context
def embeddings(ctx: click.Context, model: str, batch_size: int, limit: int | None) -> None:
    """Generate sentence-transformer embeddings for all knowledge records."""
    db_path: Path = ctx.obj["db_path"]
    click.echo(f"Generating embeddings using model: {model}")

    entity_count = build_entity_embeddings(
        db_path=db_path, model_name=model, batch_size=batch_size, limit=limit
    )
    ref_count = build_reference_embeddings(
        db_path=db_path, model_name=model, batch_size=batch_size // 2
    )

    click.echo(f"\nEmbeddings generated:")
    click.echo(f"  entities:   {entity_count:,}")
    click.echo(f"  reference:  {ref_count:,}")

    click.echo("Rebuilding FTS5 indexes...")
    rebuild_fts_indexes(db_path)
    click.echo("Done.")


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show current knowledge database statistics."""
    db_path: Path = ctx.obj["db_path"]

    if not db_path.exists():
        click.echo(f"Knowledge database not found at: {db_path}")
        click.echo("Run `forge_memory init` to create it.")
        return

    click.echo(f"Knowledge database: {db_path}")
    click.echo(f"Size: {db_path.stat().st_size / (1024**2):.1f} MB")
    click.echo("\nRecord counts:")
    counts = get_entity_count(db_path)
    for table, count in counts.items():
        if count >= 0:
            click.echo(f"  {table:<30} {count:>12,}")
        else:
            click.echo(f"  {table:<30}  (table not found)")


@cli.command("all")
@click.option("--wikidata-dump", default=None, type=click.Path(), help="Path to Wikidata dump")
@click.option("--conceptnet-csv", default=None, type=click.Path())
@click.option("--geonames-txt", default=None, type=click.Path())
@click.option("--dbpedia-json", default=None, type=click.Path())
@click.option("--skip-embeddings", is_flag=True, default=False)
@click.option("--limit", default=None, type=int, help="Limit per source (testing only)")
@click.pass_context
def build_all(
    ctx: click.Context,
    wikidata_dump: str | None,
    conceptnet_csv: str | None,
    geonames_txt: str | None,
    dbpedia_json: str | None,
    skip_embeddings: bool,
    limit: int | None,
) -> None:
    """Build the complete knowledge database from all available sources."""
    db_path: Path = ctx.obj["db_path"]

    click.echo("=" * 60)
    click.echo("ThoughtForge — Full Knowledge Forge")
    click.echo("=" * 60)
    click.echo(f"Target DB: {db_path}\n")

    # Always: init schema
    click.echo("Step 1/6: Initializing schema...")
    initialize_schema(db_path)

    # Always: reference data
    click.echo("\nStep 2/6: Ingesting reference documents...")
    ReferenceDataETL(db_path).build()

    # Optional: Wikidata
    if wikidata_dump:
        click.echo(f"\nStep 3/6: Streaming Wikidata dump ({wikidata_dump})...")
        WikidataETL(db_path).build(dump_path=wikidata_dump, limit=limit)
    else:
        click.echo("\nStep 3/6: Wikidata — skipped (no --wikidata-dump provided)")

    # Optional: ConceptNet
    if conceptnet_csv:
        click.echo(f"\nStep 4/6: Ingesting ConceptNet ({conceptnet_csv})...")
        ConceptNetETL(db_path).build(csv_path=conceptnet_csv, limit=limit)
    else:
        click.echo("\nStep 4/6: ConceptNet — skipped (no --conceptnet-csv provided)")

    # Optional: GeoNames
    if geonames_txt:
        click.echo(f"\nStep 5/6: Ingesting GeoNames ({geonames_txt})...")
        GeoNamesETL(db_path).build(txt_path=geonames_txt, limit=limit)
    else:
        click.echo("\nStep 5/6: GeoNames — skipped (no --geonames-txt provided)")

    # Embeddings + FTS index rebuild
    if not skip_embeddings:
        click.echo("\nStep 6/6: Generating embeddings + rebuilding FTS indexes...")
        build_entity_embeddings(db_path=db_path)
        build_reference_embeddings(db_path=db_path)
        rebuild_fts_indexes(db_path)
    else:
        click.echo("\nStep 6/6: Embeddings — skipped (--skip-embeddings)")

    click.echo("\n" + "=" * 60)
    click.echo("Knowledge Forge complete!")
    click.echo("=" * 60)
    ctx.invoke(status)


if __name__ == "__main__":
    cli()
