from pathlib import Path

from yggdrasil.knowledge.chart_intelligence import ChartIntelligence


def test_chart_index_reads_subfolders_as_categories(tmp_path: Path):
    charts = tmp_path / "charts"
    (charts / "culture" / "rituals").mkdir(parents=True)
    target = charts / "culture" / "rituals" / "rites.yaml"
    target.write_text(
        """
        title: Sacred Rites
        categories: [religion, ceremony]
        links:
          - charts/history/events.yaml
        details:
          - blot
          - oath
        """,
        encoding="utf-8",
    )

    index = ChartIntelligence(charts)
    result = index.query("oath ceremony", max_results=3)

    assert result["indexed_files"] == 1
    assert result["results"]
    first = result["results"][0]
    assert "culture" in first["categories"]
    assert "rituals" in first["categories"]
    assert "religion" in first["categories"]
    assert first["links"] == ["charts/history/events.yaml"]
