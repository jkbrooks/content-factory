#!/usr/bin/env python3
"""
qa.py — QA Agent

Scores drafts on quality, originality, and fit. Passes articles ≥7/10
to the publishing queue; rejects below that with actionable feedback.

Usage:
    python agents/qa.py --cluster a
    python agents/qa.py --cluster a --draft path/to/draft.md
    python agents/qa.py --cluster a --threshold 6
"""

import json
from pathlib import Path
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from shared import get_openai, paperclip_report, CLUSTER_NAMES, CLUSTER_DESCRIPTIONS

app = typer.Typer()
console = Console()

RUBRIC = """Score this newsletter article on five dimensions, each 1-10:

1. ORIGINALITY — Does this make a non-obvious point? Or is it generic?
2. CLARITY — Is the thesis clear and the argument well-structured?
3. AUDIENCE_FIT — Does this match the target audience's interests and sophistication?
4. CORPUS_GROUNDING — Does it draw on specific frameworks/ideas rather than generic content?
5. READABILITY — Is the writing tight? No fluff, no jargon abuse?

Return JSON:
{
  "scores": {
    "originality": <1-10>,
    "clarity": <1-10>,
    "audience_fit": <1-10>,
    "corpus_grounding": <1-10>,
    "readability": <1-10>
  },
  "overall": <average, 1 decimal>,
  "verdict": "pass" | "reject",
  "feedback": "<2-3 sentences of specific, actionable feedback>",
  "strongest_section": "<which section works best>",
  "weakest_section": "<which section to cut or rewrite>"
}"""


def score_draft(draft_text: str, cluster: str, client) -> dict:
    prompt = f"""Target audience: {CLUSTER_DESCRIPTIONS[cluster]}

Article to score:
---
{draft_text[:4000]}
---

{RUBRIC}"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


def pick_draft(cluster: str, draft_path: Path = None) -> tuple[str, Path]:
    if draft_path:
        return draft_path.read_text(), draft_path

    drafts_dir = Path(__file__).parent / "queue" / "drafts" / cluster
    files = sorted(drafts_dir.glob("*.md"))
    if not files:
        raise FileNotFoundError(f"No drafts in {drafts_dir}. Run writer.py first.")
    path = files[0]
    return path.read_text(), path


@app.command()
def run(
    cluster: str = typer.Option(..., "--cluster", "-c"),
    draft: Path = typer.Option(None, "--draft", help="Specific draft file to score"),
    threshold: int = typer.Option(7, "--threshold", "-t", help="Minimum score to pass (1-10)"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    task_id: str = typer.Option(None, "--task-id"),
):
    """Score a draft and route it to approved/ or rejected/."""
    if cluster not in CLUSTER_NAMES:
        console.print(f"[red]Unknown cluster '{cluster}'[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]QA Agent — Cluster {cluster.upper()} ({CLUSTER_NAMES[cluster]})[/bold]")

    client = get_openai()
    draft_text, draft_path = pick_draft(cluster, draft)

    console.print(f"Scoring: [bold]{draft_path.name}[/bold]")
    result = score_draft(draft_text, cluster, client)

    # Display scores
    table = Table(title="QA Scores")
    table.add_column("Dimension")
    table.add_column("Score", justify="right")
    for dim, score in result["scores"].items():
        color = "green" if score >= 7 else "yellow" if score >= 5 else "red"
        table.add_row(dim.replace("_", " ").title(), f"[{color}]{score}/10[/{color}]")
    table.add_row("[bold]Overall[/bold]", f"[bold]{result['overall']}/10[/bold]")
    console.print(table)

    console.print(f"\nVerdict: [bold]{'[green]PASS' if result['verdict'] == 'pass' else '[red]REJECT'}[/bold]")
    console.print(f"Feedback: {result['feedback']}")
    console.print(f"Strongest: {result.get('strongest_section', 'n/a')}")
    console.print(f"Weakest: {result.get('weakest_section', 'n/a')}")

    if dry_run:
        console.print("\n[yellow]Dry run — not routed.[/yellow]")
        return

    overall = float(result["overall"])
    passed = overall >= threshold

    base = draft_path.parent.parent
    if passed:
        dest_dir = base / "approved" / cluster
    else:
        dest_dir = base / "rejected" / cluster
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Inject QA metadata into frontmatter
    qa_note = (
        f"\n<!-- QA: {result['verdict'].upper()} | score={result['overall']} | {datetime.utcnow().date()} -->\n"
    )
    annotated = draft_text + qa_note
    dest_path = dest_dir / draft_path.name
    dest_path.write_text(annotated)
    draft_path.unlink()

    if passed:
        console.print(f"\n[green]✓ Moved to approved/ → {dest_path}[/green]")
    else:
        console.print(f"\n[red]✗ Moved to rejected/ → {dest_path}[/red]")
        console.print("[dim]Review rejected/ manually — fix and re-run writer.py, or delete.[/dim]")

    if task_id:
        verdict_str = f"PASS ({result['overall']}/10)" if passed else f"REJECT ({result['overall']}/10)"
        paperclip_report(task_id, "complete", f"QA: {draft_path.name} → {verdict_str}. {result['feedback']}")


if __name__ == "__main__":
    app()
