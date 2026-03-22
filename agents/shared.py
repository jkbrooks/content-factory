"""
shared.py — utilities shared across all agents
"""

import os
import json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")

CLUSTER_NAMES = {
    "a": "Builder",
    "b": "Thinker",
    "c": "Degen",
    "d": "Creator",
}

CLUSTER_DESCRIPTIONS = {
    "a": "AI agents, autonomous systems, org architecture, PKM. Audience: solo technical founders and AI engineers.",
    "b": "Theology, physics, consciousness, political economy. Audience: polymath intellectuals.",
    "c": "DeFi, tokenomics, crypto gaming, prediction markets. Audience: on-chain traders and protocol builders.",
    "d": "Worldbuilding, paranormal/UAP, visual AI, narrative design. Audience: creative technologists.",
}


def get_openai() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set in .env")
    return OpenAI(api_key=key)


def load_corpus(cluster: Optional[str] = None, corpus_dir: Optional[Path] = None) -> list[dict]:
    """Load all corpus chunks, optionally filtered by cluster tag."""
    if corpus_dir is None:
        corpus_dir = Path(__file__).parent.parent / "corpus"

    chunks = []
    for path in corpus_dir.rglob("*.md"):
        if "examples" in path.parts and cluster:
            pass  # include examples regardless
        text = path.read_text(encoding="utf-8", errors="replace")

        # Parse frontmatter if present
        meta = {}
        body = text
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                fm_text = text[3:end].strip()
                for line in fm_text.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip()
                body = text[end + 3:].strip()

        chunk_cluster = meta.get("cluster", "all")
        if cluster and chunk_cluster not in ("all", cluster):
            continue

        chunks.append({
            "path": str(path),
            "cluster": chunk_cluster,
            "quality": int(meta.get("quality", 5)),
            "title": meta.get("title", path.stem),
            "text": body,
        })

    return sorted(chunks, key=lambda c: c["quality"], reverse=True)


def paperclip_report(task_id: str, status: str, message: str, cost_tokens: int = 0):
    """Report progress back to Paperclip via its API."""
    import requests
    base = os.getenv("PAPERCLIP_BASE_URL", "http://localhost:3100")
    key = os.getenv("PAPERCLIP_API_KEY", "")
    if not key:
        return  # Paperclip not configured, skip
    try:
        requests.post(
            f"{base}/api/issues/{task_id}/comments",
            headers={"Authorization": f"Bearer {key}"},
            json={"body": message},
            timeout=5,
        )
    except Exception:
        pass  # Don't let Paperclip reporting failures break the agent
