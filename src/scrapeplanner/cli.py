"""Command line: ``scrapeplanner URL [--json] [--profile PATH] ...``."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from scrapeplanner import __version__, config
from scrapeplanner.analyze import InvalidURL, Options, analyze
from scrapeplanner.output.json_out import to_json
from scrapeplanner.output.profile import to_yaml
from scrapeplanner.output.terminal import render

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help=(
        "Report the cheapest reliable, polite way to collect a site's data. "
        f"Makes at most {config.MAX_REQUESTS} requests by default, reads robots.txt "
        "first and stops at the first block."
    ),
)


def _version(value: bool) -> None:
    if value:
        typer.echo(f"scrapeplanner {__version__}")
        raise typer.Exit()


@app.command()
def run(
    url: Annotated[str, typer.Argument(help="Page to analyse: a homepage or a public listing.")],
    json_output: Annotated[
        bool, typer.Option("--json", help="Print the full report as JSON instead of text.")
    ] = False,
    profile: Annotated[
        Path | None,
        typer.Option(
            "--profile",
            help="Write a starter profile.yaml to this path.",
            dir_okay=False,
            writable=True,
        ),
    ] = None,
    items: Annotated[
        int, typer.Option("--items", min=1, help="Number of records to estimate for.")
    ] = config.DEFAULT_ITEMS,
    max_requests: Annotated[
        int,
        typer.Option(
            "--max-requests",
            min=1,
            max=config.MAX_REQUESTS_CAP,
            help="Request budget for this run (every redirect hop counts).",
        ),
    ] = config.MAX_REQUESTS,
    delay: Annotated[
        float,
        typer.Option(
            "--delay", min=1.0, help="Seconds between requests (robots crawl-delay wins if larger)."
        ),
    ] = config.DELAY_SECONDS,
    timeout: Annotated[
        float, typer.Option("--timeout", min=1.0, help="Per-request timeout in seconds.")
    ] = config.TIMEOUT_SECONDS,
    record: Annotated[
        Path | None,
        typer.Option(
            "--record",
            file_okay=False,
            help="Save every HTTP exchange to this directory (for tests).",
        ),
    ] = None,
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version, is_eager=True, help="Show the version."),
    ] = None,
) -> None:
    """Analyse URL and print a collection plan."""
    options = Options(
        items=items, max_requests=max_requests, delay=delay, timeout=timeout, record_dir=record
    )
    err = Console(stderr=True)
    try:
        if not json_output:
            with err.status(f"Analysing {url} (polite: {delay:g}s between requests)"):
                report = analyze(url, options)
        else:
            report = analyze(url, options)
    except InvalidURL as exc:
        err.print(f"[red]error:[/] {exc}")
        raise typer.Exit(2) from exc
    if json_output:
        sys.stdout.write(to_json(report))
    else:
        render(report, Console())
    if profile is not None:
        profile.write_text(to_yaml(report), encoding="utf-8")
        err.print(f"profile written to {profile}")


def main() -> None:
    app()
