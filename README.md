# Content Factory

An autonomous content company that runs on AI agents. Drop in a corpus, configure four publishing channels, and let it run.

```
corpus/ → Research Agent → Writer Agent → QA Agent → Publisher Agent → Beehiiv newsletter
```

Powered by [Paperclip](https://github.com/paperclipai/paperclip) for agent orchestration.

---

## What this is

A self-contained system for running an AI-powered content business:

- **Four content clusters** — each a separate Paperclip "company" targeting a different audience
- **Automated pipeline** — agents research, write, score, and publish on a schedule
- **Corpus-driven quality** — content draws from your own source material, not generic AI output
- **Near-zero maintenance** — weekly ~30min check-in to review flagged items

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full stakeholder analysis and revenue model.

---

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/content-factory.git
cd content-factory
./setup.sh
```

### 2. Start Paperclip

```bash
cd orchestration
pnpm install
pnpm dev
```

Open [http://localhost:3100](http://localhost:3100).

### 3. Add your corpus

Put your source content (markdown files, text exports, notes) in `corpus/`. Each file becomes
available to the Research and Writer agents when generating articles. See [`corpus/README.md`](corpus/README.md).

### 4. Configure environment

```bash
cp .env.example .env
# Fill in: OPENAI_API_KEY, BEEHIIV_API_KEY, BEEHIIV_PUBLICATION_IDS
```

### 5. Create a Paperclip company

Import one of the cluster configs:

```bash
cd companies/cluster-a-builder
# Follow setup instructions in cluster README
```

### 6. Run the agents

```bash
python agents/research.py --cluster a
python agents/writer.py --cluster a
python agents/qa.py --cluster a
python agents/publisher.py --cluster a
```

Or let Paperclip schedule them on heartbeats.

---

## Structure

```
orchestration/     Paperclip control plane (full copy)
agents/            Python agent scripts (research, write, QA, publish)
corpus/            Your source content — add files here
companies/         Paperclip company configs per cluster
docs/              Architecture, playbooks, reference material
tools/             Helper scripts (corpus export, search, etc.)
.devcontainer/     Codespace / devcontainer configuration
```

---

## The four clusters

| Cluster | Audience | Content focus |
|---------|----------|---------------|
| A — Builder | AI engineers, solo founders | Agent architecture, automation, PKM |
| B — Thinker | Polymath readers | Theology, physics, consciousness, strategy |
| C — Degen | Crypto traders, protocol builders | DeFi, tokenomics, on-chain gaming |
| D — Creator | Worldbuilders, paranormal researchers | Narrative design, UAP/anomalous, visual AI |

Start with one. Prove the model. Add the others.

---

## Requirements

- Node.js 20+, pnpm 9.15+  (for Paperclip)
- Python 3.11+ (for agents)
- OpenAI API key
- Beehiiv account + API key

---

## License

MIT
