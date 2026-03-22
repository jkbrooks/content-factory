#!/usr/bin/env python3
"""
export-corpus.py

Selectively export and sanitize content from a raw corpus (ChatGPT exports,
plain text files, etc.) into the corpus/ directory for use by agents.

Usage:
    python tools/export-corpus.py --help
    python tools/export-corpus.py --source ~/path/to/individual_chats --list
    python tools/export-corpus.py \
        --source ~/path/to/individual_chats \
        --files "B Principal-agent problem vs agent.txt" \
        --cluster a \
        --out corpus/

The tool:
  1. Reads the source files
  2. Strips obvious personal identifiers (names, emails, phone numbers)
  3. Truncates to a reasonable chunk size
  4. Writes sanitized markdown to the output directory
  5. Prints a summary for your review — always check before committing
"""

import re
import sys
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Export and sanitize corpus chunks for the content factory.")
console = Console()

# ── Sanitization patterns ─────────────────────────────────────────────────────

REDACT_PATTERNS = [
    # Email addresses
    (r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "[EMAIL]"),
    # Phone numbers (US-ish)
    (r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE]"),
    # Social Security Numbers
    (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
    # Wallet addresses (Ethereum-style)
    (r"\b0x[a-fA-F0-9]{40}\b", "[WALLET]"),
    # API keys / secrets (rough heuristic: long alphanumeric strings after key= or token=)
    (r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S+", r"\1: [REDACTED]"),
]

CLUSTER_LABELS = {"a": "Builder", "b": "Thinker", "c": "Degen", "d": "Creator"}


def sanitize(text: str) -> str:
    for pattern, replacement in REDACT_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


def truncate(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    # Try to cut at a paragraph boundary
    cutoff = text[:max_chars].rfind("\n\n")
    if cutoff == -1:
        cutoff = max_chars
    return text[:cutoff] + "\n\n[... truncated ...]"


def slugify(name: str) -> str:
    name = Path(name).stem
    name = re.sub(r"[^\w\s-]", "", name.lower())
    name = re.sub(r"[\s_]+", "-", name).strip("-")
    return name


@app.command()
def export(
    source: Path = typer.Option(..., "--source", "-s", help="Directory containing source files"),
    files: list[str] = typer.Option(None, "--files", "-f", help="Specific filenames to export (repeatable)"),
    cluster: str = typer.Option(None, "--cluster", "-c", help="Cluster tag: a, b, c, or d"),
    quality: int = typer.Option(7, "--quality", "-q", help="Subjective quality score 1-10"),
    out: Path = typer.Option(Path("corpus"), "--out", "-o", help="Output directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing"),
    max_chars: int = typer.Option(6000, "--max-chars", help="Max characters per exported chunk"),
):
    """Export specific files from a corpus source directory into corpus/."""
    source = Path(source).expanduser()
    out = Path(out).expanduser()

    if not source.exists():
        console.print(f"[red]Source directory not found: {source}[/red]")
        raise typer.Exit(1)

    if not files:
        console.print("[yellow]No --files specified. Use --list to see available files.[/yellow]")
        raise typer.Exit(1)

    out.mkdir(parents=True, exist_ok=True)

    table = Table(title="Export Preview", show_lines=True)
    table.add_column("Source file")
    table.add_column("Output file")
    table.add_column("Chars (original)")
    table.add_column("Chars (exported)")
    table.add_column("Redactions")

    results = []
    for fname in files:
        src_path = source / fname
        if not src_path.exists():
            console.print(f"[yellow]⚠ Not found: {src_path}[/yellow]")
            continue

        raw = src_path.read_text(encoding="utf-8", errors="replace")
        sanitized = sanitize(raw)
        redactions = len(re.findall(r"\[(EMAIL|PHONE|SSN|WALLET|REDACTED)\]", sanitized))
        truncated = truncate(sanitized, max_chars)

        slug = slugify(fname)
        out_name = f"{slug}.md"
        out_path = out / out_name

        frontmatter_parts = []
        if cluster:
            frontmatter_parts.append(f"cluster: {cluster}")
        frontmatter_parts.append(f"quality: {quality}")
        frontmatter_parts.append(f"source_file: {fname}")
        frontmatter = "---\n" + "\n".join(frontmatter_parts) + "\n---\n\n"

        final = frontmatter + truncated

        table.add_row(
            fname[:50],
            out_name,
            str(len(raw)),
            str(len(final)),
            str(redactions) if redactions else "-",
        )
        results.append((out_path, final, redactions))

    console.print(table)

    if dry_run:
        console.print("[yellow]Dry run — nothing written.[/yellow]")
        return

    for out_path, content, redactions in results:
        out_path.write_text(content, encoding="utf-8")
        status = f"[green]✓[/green] {out_path}"
        if redactions:
            status += f" [yellow]({redactions} items redacted)[/yellow]"
        console.print(status)

    console.print(f"\n[bold]Review the output in {out}/ before committing.[/bold]")
    console.print("Look especially for proper names, project names, and financial details that pattern matching won't catch.")


@app.command("list")
def list_files(
    source: Path = typer.Option(..., "--source", "-s", help="Directory to list"),
    pattern: str = typer.Option("*", "--pattern", "-p", help="Glob pattern filter"),
):
    """List available files in a source directory."""
    source = Path(source).expanduser()
    if not source.exists():
        console.print(f"[red]Not found: {source}[/red]")
        raise typer.Exit(1)

    files = sorted(source.glob(pattern))
    console.print(f"\n[bold]{len(files)} files in {source}:[/bold]\n")
    for f in files:
        size = f.stat().st_size
        console.print(f"  {f.name:<60} {size:>8,} bytes")


if __name__ == "__main__":
    app()
