"""Report renderers: terminal, markdown, CSV, and self-contained HTML."""

from __future__ import annotations

import csv
import html
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from rich.console import Console
from rich.table import Table

TITLE = "agent-bench — report card"


def _tasks(data: dict) -> list[dict]:
    return list(data.get("tasks") or [])


def _suites(data: dict) -> list[str]:
    suites = data.get("suites")
    if suites:
        return list(suites)
    seen: list[str] = []
    for t in _tasks(data):
        s = t.get("suite")
        if s and s not in seen:
            seen.append(s)
    return seen


def _safe_mean(values: list[float]) -> float:
    values = [v for v in values if v is not None]
    return float(mean(values)) if values else 0.0


def _aggregate(data: dict) -> list[dict[str, Any]]:
    """One row per (provider, model), aggregated across all tasks."""
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for task in _tasks(data):
        groups[(task["provider"], task["model"])].append(task)

    rows: list[dict[str, Any]] = []
    for (provider, model), tasks in groups.items():
        total = len(tasks)
        passed = sum(1 for t in tasks if t.get("passed"))
        metrics = [t.get("metrics", {}) for t in tasks]
        errors = sum(1 for m in metrics if m.get("error"))
        rows.append(
            {
                "provider": provider,
                "model": model,
                "total": total,
                "passed": passed,
                "pass_rate": passed / total if total else 0.0,
                "accuracy": _safe_mean([m.get("accuracy", 0.0) for m in metrics]),
                "format": _safe_mean([m.get("format_compliance", 0.0) for m in metrics]),
                "ttft": _safe_mean([m.get("ttft_s") or 0.0 for m in metrics]),
                "total_s": _safe_mean([m.get("total_s", 0.0) for m in metrics]),
                "tokens_per_sec": _safe_mean([m.get("tokens_per_sec", 0.0) for m in metrics]),
                "cost": sum(m.get("cost_usd", 0.0) for m in metrics),
                "errors": errors,
            }
        )
    rows.sort(key=lambda r: (-r["pass_rate"], r["provider"], r["model"]))
    return rows


def _per_suite_accuracy(data: dict) -> dict[str, dict[str, float]]:
    """{provider: {suite: mean_accuracy}}."""
    buckets: dict[tuple[str, str], list[float]] = defaultdict(list)
    for t in _tasks(data):
        buckets[(t["provider"], t["suite"])].append(t.get("metrics", {}).get("accuracy", 0.0))
    out: dict[str, dict[str, float]] = defaultdict(dict)
    for (provider, suite), values in buckets.items():
        out[provider][suite] = _safe_mean(values)
    return dict(out)


# ---------- Terminal ----------


def render_terminal(data: dict, console: Console | None = None) -> None:
    console = console or Console()
    table = Table(title=TITLE)
    table.add_column("Provider")
    table.add_column("Model")
    table.add_column("Pass", justify="right")
    table.add_column("Accuracy", justify="right")
    table.add_column("Format", justify="right")
    table.add_column("TTFT (s)", justify="right")
    table.add_column("Total (s)", justify="right")
    table.add_column("tok/s", justify="right")
    table.add_column("Cost ($)", justify="right")
    table.add_column("Err", justify="right")

    for row in _aggregate(data):
        table.add_row(
            row["provider"],
            row["model"],
            f"{row['passed']}/{row['total']} ({row['pass_rate']:.0%})",
            f"{row['accuracy']:.2f}",
            f"{row['format']:.2f}",
            f"{row['ttft']:.2f}",
            f"{row['total_s']:.2f}",
            f"{row['tokens_per_sec']:.1f}",
            f"{row['cost']:.4f}",
            str(row["errors"]),
        )
    console.print(table)


# ---------- Markdown ----------


def render_markdown(data: dict) -> str:
    rows = _aggregate(data)
    lines: list[str] = [f"# {TITLE}", ""]

    lines.append(
        "| Provider | Model | Pass | Accuracy | Format | TTFT (s) | Total (s) | tok/s | Cost ($) | Err |"
    )
    lines.append(
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    for row in rows:
        lines.append(
            f"| {row['provider']} | {row['model']} | "
            f"{row['passed']}/{row['total']} ({row['pass_rate']:.0%}) | "
            f"{row['accuracy']:.2f} | {row['format']:.2f} | "
            f"{row['ttft']:.2f} | {row['total_s']:.2f} | "
            f"{row['tokens_per_sec']:.1f} | {row['cost']:.4f} | {row['errors']} |"
        )

    per_suite = _per_suite_accuracy(data)
    suites = _suites(data)
    if per_suite and suites:
        lines.extend(["", "## Accuracy by suite", ""])
        header = "| Provider | " + " | ".join(suites) + " |"
        sep = "| --- | " + " | ".join("---:" for _ in suites) + " |"
        lines.append(header)
        lines.append(sep)
        for provider in sorted(per_suite):
            cells = [f"{per_suite[provider].get(s, 0.0):.2f}" for s in suites]
            lines.append(f"| {provider} | " + " | ".join(cells) + " |")

    return "\n".join(lines) + "\n"


def write_markdown(data: dict, path: str | Path) -> None:
    Path(path).write_text(render_markdown(data))


# ---------- CSV ----------


CSV_FIELDS = [
    "suite",
    "task_id",
    "provider",
    "model",
    "passed",
    "accuracy",
    "format_compliance",
    "ttft_s",
    "total_s",
    "prompt_tokens",
    "completion_tokens",
    "tokens_per_sec",
    "cost_usd",
    "error",
]


def write_csv(data: dict, path: str | Path) -> None:
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for task in _tasks(data):
            m = task.get("metrics", {})
            writer.writerow(
                {
                    "suite": task.get("suite", ""),
                    "task_id": task.get("task_id", ""),
                    "provider": task.get("provider", ""),
                    "model": task.get("model", ""),
                    "passed": task.get("passed", False),
                    "accuracy": m.get("accuracy", 0.0),
                    "format_compliance": m.get("format_compliance", 0.0),
                    "ttft_s": m.get("ttft_s") or "",
                    "total_s": m.get("total_s", 0.0),
                    "prompt_tokens": m.get("prompt_tokens", 0),
                    "completion_tokens": m.get("completion_tokens", 0),
                    "tokens_per_sec": m.get("tokens_per_sec", 0.0),
                    "cost_usd": m.get("cost_usd", 0.0),
                    "error": m.get("error") or "",
                }
            )


# ---------- HTML ----------


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; color: #222; }}
  h1 {{ margin-bottom: 0.25rem; }}
  table {{ border-collapse: collapse; margin: 1rem 0; }}
  th, td {{ border: 1px solid #ddd; padding: 0.4rem 0.75rem; text-align: right; }}
  th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) {{ text-align: left; }}
  thead {{ background: #f6f8fa; }}
  .charts {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1.5rem; max-width: 1100px; }}
  .chart-card {{ border: 1px solid #eee; border-radius: 8px; padding: 1rem; }}
  .chart-card h3 {{ margin: 0 0 0.5rem 0; font-size: 0.95rem; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p>{summary}</p>

<h2>Overall</h2>
{table_html}

<h2>Charts</h2>
<div class="charts">
  <div class="chart-card"><h3>Accuracy</h3><canvas id="c-accuracy"></canvas></div>
  <div class="chart-card"><h3>Total latency (s)</h3><canvas id="c-latency"></canvas></div>
  <div class="chart-card"><h3>Throughput (tok/s)</h3><canvas id="c-throughput"></canvas></div>
  <div class="chart-card"><h3>Total cost (USD)</h3><canvas id="c-cost"></canvas></div>
  <div class="chart-card" style="grid-column: 1 / -1;"><h3>Accuracy by suite</h3><canvas id="c-radar"></canvas></div>
</div>

<script>
const ROWS = {rows_json};
const SUITES = {suites_json};
const PER_SUITE = {per_suite_json};
const labels = ROWS.map(r => r.provider + " / " + r.model);

function bar(id, label, values) {{
  new Chart(document.getElementById(id), {{
    type: "bar",
    data: {{ labels, datasets: [{{ label, data: values }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }},
  }});
}}

bar("c-accuracy", "Accuracy", ROWS.map(r => r.accuracy));
bar("c-latency", "Total (s)", ROWS.map(r => r.total_s));
bar("c-throughput", "tok/s", ROWS.map(r => r.tokens_per_sec));
bar("c-cost", "Cost ($)", ROWS.map(r => r.cost));

new Chart(document.getElementById("c-radar"), {{
  type: "radar",
  data: {{
    labels: SUITES,
    datasets: ROWS.map((r, i) => ({{
      label: r.provider + " / " + r.model,
      data: SUITES.map(s => (PER_SUITE[r.provider] || {{}})[s] || 0),
      fill: true,
    }})),
  }},
  options: {{ responsive: true, scales: {{ r: {{ suggestedMin: 0, suggestedMax: 1 }} }} }},
}});
</script>
</body>
</html>
"""


def _html_table(rows: list[dict[str, Any]]) -> str:
    head = (
        "<table><thead><tr>"
        "<th>Provider</th><th>Model</th><th>Pass</th><th>Accuracy</th><th>Format</th>"
        "<th>TTFT (s)</th><th>Total (s)</th><th>tok/s</th><th>Cost ($)</th><th>Err</th>"
        "</tr></thead><tbody>"
    )
    body: list[str] = []
    for r in rows:
        body.append(
            "<tr>"
            f"<td>{html.escape(r['provider'])}</td>"
            f"<td>{html.escape(r['model'])}</td>"
            f"<td>{r['passed']}/{r['total']} ({r['pass_rate']:.0%})</td>"
            f"<td>{r['accuracy']:.2f}</td>"
            f"<td>{r['format']:.2f}</td>"
            f"<td>{r['ttft']:.2f}</td>"
            f"<td>{r['total_s']:.2f}</td>"
            f"<td>{r['tokens_per_sec']:.1f}</td>"
            f"<td>{r['cost']:.4f}</td>"
            f"<td>{r['errors']}</td>"
            "</tr>"
        )
    return head + "".join(body) + "</tbody></table>"


def render_html(data: dict) -> str:
    rows = _aggregate(data)
    suites = _suites(data)
    per_suite = _per_suite_accuracy(data)
    summary = (
        f"{len(_tasks(data))} tasks · {len(rows)} provider(s) · "
        f"{len(suites)} suite(s) · {data.get('duration_s', 0.0):.2f}s"
    )
    return _HTML_TEMPLATE.format(
        title=TITLE,
        summary=html.escape(summary),
        table_html=_html_table(rows),
        rows_json=json.dumps(rows),
        suites_json=json.dumps(suites),
        per_suite_json=json.dumps(per_suite),
    )


def write_html(data: dict, path: str | Path) -> None:
    Path(path).write_text(render_html(data))


__all__ = [
    "render_html",
    "render_markdown",
    "render_terminal",
    "write_csv",
    "write_html",
    "write_markdown",
]
