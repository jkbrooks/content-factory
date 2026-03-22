# corpus/

This directory holds the source content that agents draw on when generating articles.

## Structure

```
corpus/
├── README.md          (this file)
├── examples/          2-3 sample chunks showing the expected format
├── source/            symlink → your local corpus (created by setup.sh, never committed)
└── private/           gitignored — put anything sensitive here during local dev
```

## What goes here

Each file should be a self-contained chunk of thinking on one topic — roughly 500–3,000 words. Plain markdown or plain text. The agents use semantic search to find the most relevant chunks for a given article outline, so the better the content, the better the articles.

Good candidates:
- Your own writing, notes, essays, long-form chat exports
- Annotated summaries of papers or books you've read
- Frameworks or mental models you've developed
- Conversations that arrived at a non-obvious insight

Bad candidates:
- Raw transcripts with lots of filler ("um", "yeah", "so basically")
- Anything with personal names, private project details, or financial info
- Very short fragments (< 200 words) — too little signal

## Adding content

### Option A — manual
Drop `.md` or `.txt` files directly into this directory. Name them descriptively:
```
corpus/principal-agent-problem-ai-framing.md
corpus/entropy-shearing-systems-design.md
```

### Option B — export script
Use the export tool to selectively pull and sanitize chunks from a larger corpus:
```bash
python tools/export-corpus.py \
  --source /path/to/your/chatgpt/individual_chats \
  --cluster a \
  --files "B Principal-agent problem vs agent.txt" "P7 Principles of well-functioning systems.txt" \
  --out corpus/
```

The tool strips obvious personal identifiers before writing. Review the output before committing.

## Cluster tagging

Optionally add a frontmatter tag so agents know which cluster a chunk belongs to:

```markdown
---
cluster: a  # a=Builder, b=Thinker, c=Degen, d=Creator
quality: 8  # 1-10, your subjective rating
---

Your content here...
```

Untagged files are treated as relevant to all clusters.
