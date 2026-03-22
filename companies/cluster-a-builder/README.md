# Cluster A — The Builder

**Audience**: Solo technical founders, AI engineers, operators building with agents  
**Content focus**: Agent architecture, automation playbooks, PKM, company-of-one ops  
**Newsletter cadence**: Weekly (Tuesdays)

## Beehiiv setup

1. Create a new publication in Beehiiv
2. Name it something like "Agentic Weekly" or your own brand
3. Copy the publication ID from Settings → General
4. Add to `.env`: `BEEHIIV_PUB_CLUSTER_A=pub_XXXXXX`

## Paperclip company setup

Create a new company in Paperclip (http://localhost:3100):

- **Company goal**: "Publish one high-quality newsletter per week for technical founders and AI engineers, growing to 10,000 subscribers within 12 months."
- **CEO agent**: Weekly heartbeat, reviews metrics, reprioritizes Research focus
- **Research agent**: Daily heartbeat, scans feeds + corpus, creates article outlines
- **Writer agent**: Triggered by new outlines, produces drafts
- **QA agent**: Triggered by new drafts, scores and routes
- **Publisher agent**: Tuesday 8am heartbeat, publishes top approved article

## Agent heartbeat commands

```bash
# Research (daily)
python agents/research.py --cluster a --count 2

# Writer (daily, after research)
python agents/writer.py --cluster a

# QA (daily, after writer)
python agents/qa.py --cluster a --threshold 7

# Publisher (weekly, Tuesday morning)
python agents/publisher.py --cluster a --schedule "$(date -u +%Y-%m-%dT09:00:00Z)"
```

## Corpus sources (Cluster A)

Good content to export for this cluster:
- `B Principal-agent problem vs agent.txt` — the B1 essay
- `P Principles of well-functioning systems.txt` — P7
- `P Social network AI companionship.txt` — P6
- `Iterative decomposition process - Directed Evolutionary Swarms.txt`
- `Supremely agentic human strategy.txt`
- `Sovereignty through task scaling.txt`

Export with:
```bash
python tools/export-corpus.py \
  --source ~/path/to/chatgpt/individual_chats \
  --cluster a \
  --files "B Principal-agent problem vs agent.txt" \
          "P Principles of well-functioning systems.txt" \
  --out corpus/
```

## Target sponsors

- AI tooling companies (LangChain, CrewAI, Cursor, Replit, E2B)
- SaaS infrastructure (Vercel, Supabase, Modal)
- Dev-focused B2B SaaS generally
- CPM target: $40-60
