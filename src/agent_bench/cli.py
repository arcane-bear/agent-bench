"""Command-line interface for agent-bench."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from agent_bench import __version__
from agent_bench.core import BenchmarkRunner, RunResult
from agent_bench.custom import load_custom_suite
from agent_bench.providers import load_provider
from agent_bench.reports import (
    render_terminal,
    write_csv,
    write_html,
    write_markdown,
)
from agent_bench.suites import BUILTIN_SUITES, load_suite

console = Console()


@click.group(help="agent-bench — benchmark LLM agents on speed, cost, and quality.")
@click.version_option(__version__, prog_name="agent-bench")
def main() -> None:
    pass


def _parse_list(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


@main.command(help="Run a benchmark across one or more providers.")
@click.option(
    "--providers",
    "-p",
    required=True,
    help="Comma-separated provider specs, e.g. `openai,anthropic:claude-haiku-4-5`.",
)
@click.option(
    "--suite",
    "-s",
    "suite_names",
    multiple=True,
    help=f"Built-in suite name. Repeatable. One of: {', '.join(sorted(BUILTIN_SUITES))}.",
)
@click.option(
    "--custom",
    "custom_paths",
    multiple=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to a custom YAML suite. Repeatable.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("results.json"),
    show_default=True,
    help="Where to write the raw results JSON.",
)
@click.option("--html", type=click.Path(dir_okay=False, path_type=Path), help="HTML report path.")
@click.option("--md", type=click.Path(dir_okay=False, path_type=Path), help="Markdown report path.")
@click.option("--csv", type=click.Path(dir_okay=False, path_type=Path), help="CSV report path.")
@click.option("--quiet", is_flag=True, help="Suppress per-task progress output.")
def run(
    providers: str,
    suite_names: tuple[str, ...],
    custom_paths: tuple[Path, ...],
    output: Path,
    html: Path | None,
    md: Path | None,
    csv: Path | None,
    quiet: bool,
) -> None:
    provider_specs = _parse_list(providers)
    if not provider_specs:
        raise click.UsageError("--providers must list at least one provider.")
    if not suite_names and not custom_paths:
        raise click.UsageError("Provide at least one --suite or --custom YAML path.")

    try:
        loaded_providers = [load_provider(spec) for spec in provider_specs]
    except Exception as e:
        raise click.ClickException(f"Failed to load providers: {e}") from e

    suites = [load_suite(name) for name in suite_names]
    for path in custom_paths:
        suites.append(load_custom_suite(path))

    runner = BenchmarkRunner(providers=loaded_providers, suites=suites)

    def progress(suite: str, task_id: str, provider: str) -> None:
        if not quiet:
            console.print(f"[dim]· {provider} → {suite}/{task_id}[/dim]")

    console.print(
        f"[bold]Running[/bold] {len(suites)} suite(s) × {len(loaded_providers)} provider(s)"
    )
    result: RunResult = runner.run(verbose_cb=progress)
    result.save(output)
    console.print(f"[green]✓[/green] Raw results written to [bold]{output}[/bold]")

    data = RunResult.load(output)
    render_terminal(data, console=console)

    if md:
        write_markdown(data, md)
        console.print(f"[green]✓[/green] Markdown report: [bold]{md}[/bold]")
    if csv:
        write_csv(data, csv)
        console.print(f"[green]✓[/green] CSV report: [bold]{csv}[/bold]")
    if html:
        write_html(data, html)
        console.print(f"[green]✓[/green] HTML report: [bold]{html}[/bold]")


@main.command(help="Render a report from an existing results.json file.")
@click.argument("results", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--html", type=click.Path(dir_okay=False, path_type=Path), help="HTML report path.")
@click.option("--md", type=click.Path(dir_okay=False, path_type=Path), help="Markdown report path.")
@click.option("--csv", type=click.Path(dir_okay=False, path_type=Path), help="CSV report path.")
@click.option("--terminal/--no-terminal", default=True, help="Print the terminal report.")
def report(
    results: Path,
    html: Path | None,
    md: Path | None,
    csv: Path | None,
    terminal: bool,
) -> None:
    data = RunResult.load(results)
    if terminal:
        render_terminal(data, console=console)
    if md:
        write_markdown(data, md)
        console.print(f"[green]✓[/green] Markdown report: [bold]{md}[/bold]")
    if csv:
        write_csv(data, csv)
        console.print(f"[green]✓[/green] CSV report: [bold]{csv}[/bold]")
    if html:
        write_html(data, html)
        console.print(f"[green]✓[/green] HTML report: [bold]{html}[/bold]")


@main.command(name="list-suites", help="List built-in suites.")
def list_suites() -> None:
    for name, cls in sorted(BUILTIN_SUITES.items()):
        instance = cls()
        console.print(f"[bold]{name}[/bold] — {len(instance.tasks())} tasks")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
