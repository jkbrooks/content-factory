#!/usr/bin/env python3
"""
research.py — Research Agent

Scans external feeds (RSS, HN, arXiv) for timely hooks, matches them against
the corpus, and generates article outlines that the Writer agent picks up.

Each outline is written to agents/queue/outlines/<cluster>/<slug>.json.

Usage:
    python agents/research.py --cluster a
    python agents/research.py --cluster a --dry-run
    python agents/research.py --cluster a --count 3
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path

import typer
import feedparser
from rich.console import Console
from rich.panel import Panel

from shared import (
    get_openai, load_corpus, paperclip_report,
    CLUSTER_NAMES, CLUSTER_DESCRIPTIONS
)

app = typer.Typer()
console = Console()

# ── RSS feeds per cluster ─────────────────────────────────────────────────────

FEEDS = {
    "a": [
        "https://news.ycombinator.com/rss",
        "https://simonwillison.net/atom/everything/",
        "https://www.latent.space/feed",
    ],
    "b": [
        "https://news.ycombinator.com/rss",
        "https://quanta magazine.org/feed/",
        "https://www.lesswrong.com/feed.xml?view=top-questions",
    ],
    "c": [
        "https://news.ycombinator.com/rss",
        "https://thedefiant.io/feed",
        "https://decrypt.co/feed",
    ],
    "d": [
        "https://news.ycombinator.com/rss",
        "https://www.vice.com/en/topic/ufo/rss",
    ],
}

OUTLINE_SCHEMA = {
    "title": "str — working article title",
    "hook": "str — why this is interesting RIGHT NOW (the timely angle)",
    "thesis": "str — the single key insight this article will make",
    "corpus_chunks": "list[str] — titles of corpus chunks to draw on",
    "outline": "list[str] — 4-6 section headings",
    "target_words": "int — suggested length (800-1500)",
    "cluster": "str",
    "created_at": "ISO timestamp",
}


def fetch_feed_items(cluster: str, max_per_feed: int = 5) -> list[dict]:
    items = []
    for url in FEEDS.get(cluster, []):
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_feed]:
                items.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:500],
                    "link": entry.get("link", ""),
                    "source": feed.feed.get("title", url),
                })
        except Exception as e:
            console.print(f"[yellow]Feed error ({url}): {e}[/yellow]")
    return items


def generate_outline(
    cluster: str,
    feed_items: list[dict],
    corpus_chunks: list[dict],
    client,
) -> dict:
    cluster_desc = CLUSTER_DESCRIPTIONS[cluster]
    corpus_titles = [c["title"] for c in corpus_chunks[:10]]
    feed_summary = "\n".join(
        f"- [{i['source']}] {i['title']}: {i['summary'][:200]}"
        for i in feed_items[:8]
    )

    prompt = f"""You are an editorial research agent for a content cluster targeting: {cluster_desc}

Here are the latest items from relevant feeds:
{feed_summary}

Here are available corpus chunks you can draw on (use them to add original insight):
{chr(10).join(f"- {t}" for t in corpus_titles)}

Generate ONE article outline in JSON matching this schema:
{json.dumps(OUTLINE_SCHEMA, indent=2)}

Requirements:
- The hook must be tied to a specific timely feed item
- The thesis must be non-obvious and draw on corpus material
- corpus_chunks should list 2-4 chunk titles from the available list above
- The outline sections should be specific, not generic
- target_words: 1000-1400

Return ONLY valid JSON, no markdown fences."""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    outline = json.loads(resp.choices[0].message.content)
    outline["cluster"] = cluster
    outline["created_at"] = datetime.utcnow().isoformat()
    return outline


@app.command()
def run(
    cluster: str = typer.Option(..., "--cluster", "-c", help="Cluster: a, b, c, or d"),
    count: int = typer.Option(1, "--count", "-n", help="Number of outlines to generate"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print outline without saving"),
    task_id: str = typer.Option(None, "--task-id", help="Paperclip task ID for reporting"),
):
    """Generate article outlines from feeds + corpus."""
    if cluster not in CLUSTER_NAMES:
        console.print(f"[red]Unknown cluster '{cluster}'. Use: a, b, c, d[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Research Agent — Cluster {cluster.upper()} ({CLUSTER_NAMES[cluster]})[/bold]")

    client = get_openai()
    corpus = load_corpus(cluster)
    console.print(f"Loaded {len(corpus)} corpus chunks")

    feed_items = fetch_feed_items(cluster)
    console.print(f"Fetched {len(feed_items)} feed items from {len(FEEDS.get(cluster, []))} feeds")

    outlines_dir = Path(__file__).parent / "queue" / "outlines" / cluster
    outlines_dir.mkdir(parents=True, exist_ok=True)

    for i in range(count):
        console.print(f"\n[dim]Generating outline {i + 1}/{count}...[/dim]")
        outline = generate_outline(cluster, feed_items, corpus, client)

        slug = hashlib.md5(outline["title"].encode()).hexdigest()[:8]
        out_path = outlines_dir / f"{slug}.json"

        console.print(Panel(
            f"[bold]{outline['title']}[/bold]\n\n"
            f"Hook: {outline.get('hook', '')}\n\n"
            f"Thesis: {outline.get('thesis', '')}\n\n"
            f"Sections: {', '.join(outline.get('outline', []))}",
            title=f"Outline {i + 1}",
        ))

        if dry_run:
            console.print("[yellow]Dry run — not saved.[/yellow]")
        else:
            out_path.write_text(json.dumps(outline, indent=2))
            console.print(f"[green]Saved → {out_path}[/green]")
            if task_id:
                paperclip_report(task_id, "progress", f"Generated outline: {outline['title']}")

    if task_id:
        paperclip_report(task_id, "complete", f"Research agent done: {count} outlines for cluster {cluster}")


if __name__ == "__main__":
    app()
