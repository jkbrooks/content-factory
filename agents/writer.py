#!/usr/bin/env python3
"""
writer.py — Writer Agent

Picks up outlines from agents/queue/outlines/<cluster>/ and writes full
articles, saving drafts to agents/queue/drafts/<cluster>/<slug>.md.

Usage:
    python agents/writer.py --cluster a
    python agents/writer.py --cluster a --outline path/to/outline.json
    python agents/writer.py --cluster a --dry-run
"""

import json
from pathlib import Path
from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel

from shared import (
    get_openai, load_corpus, paperclip_report,
    CLUSTER_NAMES, CLUSTER_DESCRIPTIONS
)

app = typer.Typer()
console = Console()

WRITER_SYSTEM_PROMPT = """You are a skilled writer producing content for a niche newsletter.
Your writing draws on the author's own frameworks and ideas, not generic knowledge.

Style rules:
- No fluff. Every sentence earns its place.
- Concrete before abstract. Ground claims in examples, numbers, or mechanisms.
- The author's voice is direct, precise, and comfortable with complexity.
- No hype, no clickbait in the body. The hook is earned by the substance.
- Short paragraphs (2-4 sentences). One idea per paragraph.
- Bold sparingly — only for genuinely important terms or takeaways.
- No em-dash abuse. Vary sentence structure instead.
- End with something that opens a door, not a listicle of "key takeaways."

Format:
- H2 for main sections (##)
- H3 for subsections if needed (###)
- No H1 — the title is in frontmatter
- Include a "---" break before a short closing paragraph
"""


def pick_outline(cluster: str, outline_path: Path = None) -> tuple[dict, Path]:
    if outline_path:
        return json.loads(outline_path.read_text()), outline_path

    outlines_dir = Path(__file__).parent / "queue" / "outlines" / cluster
    files = sorted(outlines_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No outlines in {outlines_dir}. Run research.py first.")
    path = files[0]
    return json.loads(path.read_text()), path


def retrieve_corpus_context(outline: dict, corpus: list[dict]) -> str:
    wanted = set(outline.get("corpus_chunks", []))
    if not wanted:
        # Fall back to top quality chunks
        return "\n\n---\n\n".join(c["text"][:1500] for c in corpus[:3])
    matched = [c for c in corpus if c["title"] in wanted]
    if not matched:
        matched = corpus[:3]
    return "\n\n---\n\n".join(c["text"][:2000] for c in matched)


def write_article(outline: dict, corpus_context: str, client) -> str:
    cluster = outline["cluster"]
    sections = "\n".join(f"- {s}" for s in outline.get("outline", []))

    prompt = f"""Write a complete article for a {CLUSTER_DESCRIPTIONS[cluster]} newsletter.

Title: {outline['title']}
Hook / angle: {outline['hook']}
Central thesis: {outline['thesis']}
Target length: {outline.get('target_words', 1200)} words

Sections to cover:
{sections}

Draw on this material from the author's own writing (paraphrase and integrate, don't quote verbatim):
---
{corpus_context}
---

Write the full article now. Return only the article body (no frontmatter, no title heading)."""

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": WRITER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
    )
    return resp.choices[0].message.content.strip()


def build_frontmatter(outline: dict) -> str:
    return (
        f"---\n"
        f"title: \"{outline['title']}\"\n"
        f"cluster: {outline['cluster']}\n"
        f"status: draft\n"
        f"created_at: {datetime.utcnow().isoformat()}\n"
        f"---\n\n"
    )


@app.command()
def run(
    cluster: str = typer.Option(..., "--cluster", "-c"),
    outline: Path = typer.Option(None, "--outline", help="Specific outline file to write"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    task_id: str = typer.Option(None, "--task-id"),
):
    """Write a full article draft from an outline."""
    if cluster not in CLUSTER_NAMES:
        console.print(f"[red]Unknown cluster '{cluster}'[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Writer Agent — Cluster {cluster.upper()} ({CLUSTER_NAMES[cluster]})[/bold]")

    client = get_openai()
    corpus = load_corpus(cluster)

    outline_data, outline_path = pick_outline(cluster, outline)
    console.print(f"Writing: [bold]{outline_data['title']}[/bold]")

    context = retrieve_corpus_context(outline_data, corpus)
    console.print(f"Corpus context: {len(context)} chars from {len(outline_data.get('corpus_chunks', []))} chunks")

    article_body = write_article(outline_data, context, client)
    full_article = build_frontmatter(outline_data) + article_body

    word_count = len(article_body.split())
    console.print(Panel(
        article_body[:600] + "\n\n[dim]... (truncated preview)[/dim]",
        title=f"Draft preview ({word_count} words)",
    ))

    drafts_dir = Path(__file__).parent / "queue" / "drafts" / cluster
    drafts_dir.mkdir(parents=True, exist_ok=True)
    slug = outline_path.stem
    draft_path = drafts_dir / f"{slug}.md"

    if dry_run:
        console.print("[yellow]Dry run — not saved.[/yellow]")
    else:
        draft_path.write_text(full_article)
        console.print(f"[green]Draft saved → {draft_path}[/green]")
        # Move outline to processed/
        processed = outline_path.parent.parent / "processed" / cluster
        processed.mkdir(parents=True, exist_ok=True)
        outline_path.rename(processed / outline_path.name)
        if task_id:
            paperclip_report(task_id, "complete", f"Draft written: {outline_data['title']} ({word_count} words)")


if __name__ == "__main__":
    app()
