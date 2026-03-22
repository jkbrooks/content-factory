#!/usr/bin/env python3
"""
publisher.py — Publisher Agent

Takes the top approved article and publishes it to Beehiiv.
Optionally generates social snippets for X/LinkedIn.

Usage:
    python agents/publisher.py --cluster a
    python agents/publisher.py --cluster a --dry-run
    python agents/publisher.py --cluster a --schedule "2026-03-25T09:00:00Z"
"""

import os
import re
import json
import requests
from pathlib import Path
from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel

from shared import get_openai, paperclip_report, CLUSTER_NAMES

app = typer.Typer()
console = Console()

BEEHIIV_API = "https://api.beehiiv.com/v2"

PUB_ID_KEYS = {
    "a": "BEEHIIV_PUB_CLUSTER_A",
    "b": "BEEHIIV_PUB_CLUSTER_B",
    "c": "BEEHIIV_PUB_CLUSTER_C",
    "d": "BEEHIIV_PUB_CLUSTER_D",
}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    meta, body = {}, text
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            for line in text[3:end].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"')
            body = text[end + 3:].strip()
    return meta, body


def markdown_to_html(text: str) -> str:
    """Minimal markdown → HTML for Beehiiv's content field."""
    lines, html = text.splitlines(), []
    for line in lines:
        if line.startswith("## "):
            html.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            html.append(f"<h3>{line[4:]}</h3>")
        elif line.strip() == "---":
            html.append("<hr>")
        elif line.strip() == "":
            html.append("<br>")
        else:
            # Bold
            line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            # Italic
            line = re.sub(r"\*(.+?)\*", r"<em>\1</em>", line)
            html.append(f"<p>{line}</p>")
    return "\n".join(html)


def generate_social_snippets(title: str, body: str, cluster: str, client) -> list[str]:
    prompt = f"""Given this article for a {cluster} newsletter, write 5 tweet-length (≤280 chars) hooks.
Each hook should stand alone, be specific, and make someone want to read the article.
No hashtags. No "thread 🧵". No emojis unless natural.
Return a JSON array of 5 strings.

Title: {title}
Article excerpt:
{body[:1500]}"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    # Handle both {"snippets": [...]} and bare array
    if isinstance(data, list):
        return data
    return data.get("snippets", data.get("hooks", list(data.values())[0]))


def publish_to_beehiiv(
    pub_id: str, api_key: str,
    title: str, html_body: str,
    schedule_at: str = None,
    preview_text: str = "",
) -> dict:
    endpoint = f"{BEEHIIV_API}/publications/{pub_id}/posts"
    payload = {
        "title": title,
        "content": html_body,
        "status": "draft" if not schedule_at else "scheduled",
        "preview_text": preview_text[:200] if preview_text else title,
        "authors": [],
    }
    if schedule_at:
        payload["scheduled_at"] = schedule_at

    resp = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def pick_approved(cluster: str) -> tuple[str, Path]:
    approved_dir = Path(__file__).parent / "queue" / "approved" / cluster
    files = sorted(approved_dir.glob("*.md"))
    if not files:
        raise FileNotFoundError(f"No approved articles in {approved_dir}. Run qa.py first.")
    path = files[0]
    return path.read_text(), path


@app.command()
def run(
    cluster: str = typer.Option(..., "--cluster", "-c"),
    article: Path = typer.Option(None, "--article", help="Specific approved article to publish"),
    schedule: str = typer.Option(None, "--schedule", help="ISO 8601 UTC time to schedule send"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    social: bool = typer.Option(True, "--social/--no-social", help="Generate social snippets"),
    task_id: str = typer.Option(None, "--task-id"),
):
    """Publish the top approved article to Beehiiv."""
    if cluster not in CLUSTER_NAMES:
        console.print(f"[red]Unknown cluster '{cluster}'[/red]")
        raise typer.Exit(1)

    api_key = os.getenv("BEEHIIV_API_KEY")
    pub_id = os.getenv(PUB_ID_KEYS[cluster])

    if not api_key or not pub_id:
        console.print(f"[red]Missing BEEHIIV_API_KEY or {PUB_ID_KEYS[cluster]} in .env[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Publisher Agent — Cluster {cluster.upper()} ({CLUSTER_NAMES[cluster]})[/bold]")

    if article:
        draft_text, draft_path = article.read_text(), article
    else:
        draft_text, draft_path = pick_approved(cluster)

    meta, body = parse_frontmatter(draft_text)
    title = meta.get("title", draft_path.stem)

    console.print(f"Publishing: [bold]{title}[/bold]")

    html_body = markdown_to_html(body)
    preview = body[:200].replace("\n", " ").strip()

    console.print(Panel(body[:400] + "\n[dim]...[/dim]", title="Article preview"))

    # Social snippets
    if social:
        client = get_openai()
        snippets = generate_social_snippets(title, body, cluster, client)
        console.print("\n[bold]Social snippets:[/bold]")
        for i, s in enumerate(snippets, 1):
            console.print(f"  {i}. {s}")

        snippets_path = draft_path.parent / f"{draft_path.stem}-social.json"
        if not dry_run:
            snippets_path.write_text(json.dumps(snippets, indent=2))

    if dry_run:
        console.print("\n[yellow]Dry run — not published to Beehiiv.[/yellow]")
        return

    result = publish_to_beehiiv(pub_id, api_key, title, html_body, schedule, preview)
    post_id = result.get("data", {}).get("id", "unknown")
    console.print(f"\n[green]✓ Published to Beehiiv. Post ID: {post_id}[/green]")

    # Archive the article
    archive_dir = draft_path.parent.parent / "published" / cluster
    archive_dir.mkdir(parents=True, exist_ok=True)
    draft_path.rename(archive_dir / draft_path.name)
    console.print(f"[dim]Archived → {archive_dir / draft_path.name}[/dim]")

    if task_id:
        paperclip_report(task_id, "complete", f"Published: '{title}' (Beehiiv post {post_id})")


if __name__ == "__main__":
    app()
