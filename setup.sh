#!/usr/bin/env bash
# setup.sh — bootstraps the content factory for local dev or Codespaces
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_PPM_SCRATCH="$HOME/Desktop/dev/active/personal_project_management/scratch"

echo "=== Content Factory Setup ==="

# ── Corpus ───────────────────────────────────────────────────────────────────
# Locally: create a symlink into the scratch corpus if it exists.
# In Codespaces / fresh clone: corpus/ stays as the plain directory.
# Either way, the agents look at corpus/ — it just may be empty until you
# populate it with `tools/export-corpus.py`.

CORPUS_SRC="$LOCAL_PPM_SCRATCH/organizational-architecture/corpus"
CORPUS_DEST="$REPO_ROOT/corpus/source"

if [ -d "$CORPUS_SRC" ] && [ ! -L "$CORPUS_DEST" ]; then
  echo "→ Local corpus found. Creating symlink: corpus/source → $CORPUS_SRC"
  ln -sf "$CORPUS_SRC" "$CORPUS_DEST"
elif [ -L "$CORPUS_DEST" ]; then
  echo "→ corpus/source symlink already exists ($(readlink "$CORPUS_DEST"))"
else
  echo "→ No local corpus found. corpus/source will be populated manually."
  echo "  Run: python tools/export-corpus.py --help"
fi

# ── Python deps ───────────────────────────────────────────────────────────────
if [ -f "$REPO_ROOT/requirements.txt" ]; then
  echo "→ Installing Python dependencies..."
  pip install -r "$REPO_ROOT/requirements.txt" -q
fi

# ── Paperclip / Orchestration ─────────────────────────────────────────────────
if [ -f "$REPO_ROOT/orchestration/package.json" ]; then
  echo "→ Installing Paperclip dependencies..."
  (cd "$REPO_ROOT/orchestration" && pnpm install --silent)
  echo "  Start Paperclip with: cd orchestration && pnpm dev"
fi

# ── .env ──────────────────────────────────────────────────────────────────────
if [ ! -f "$REPO_ROOT/.env" ]; then
  echo "→ Copying .env.example → .env (fill in your API keys)"
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Fill in .env with your API keys"
echo "  2. Add content to corpus/ (or run tools/export-corpus.py)"
echo "  3. cd orchestration && pnpm dev"
echo "  4. Open http://localhost:3100 and create a company"
echo "  5. python agents/research.py --cluster a --dry-run"
