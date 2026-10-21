#!/bin/bash
# backup_milestone.sh — Wipe-proof milestone backup (run after EVERY milestone)
# Usage: bash scripts/backup_milestone.sh "label text"
# 1) git commit+push code/docs (data/ gitignored)  2) tarball key artifacts to download/backups/
# 3) sha256 ledger  4) append to worklog  5) verify push, warn on failure
set -uo pipefail
cd /home/z/my-project
LABEL="${1:-milestone}"
TS=$(date -u +%Y%m%d_%H%M%S)
LOG=/home/z/my-project/worklog.md
FAIL=0

echo "[backup] milestone: $LABEL @ $TS"

# --- 1) git commit + push ---------------------------------------------------
if [ -n "$(git status --porcelain -- . ':!data' ':!download' ':!upload' ':!workspace' 2>/dev/null)" ]; then
  git add plan.md worklog.md HANDOFF.md README.md requirements.txt .gitignore \
          scripts/ src/ docs/ download/ .github/ "Users note on r4 previous findings" 2>/dev/null
  git commit -m "milestone: ${LABEL} (${TS})" >/dev/null 2>&1 || echo "[backup] nothing new to commit (code/docs)"
fi
if git push origin main >/tmp/pushlog 2>&1; then
  echo "[backup] git push OK"
else
  echo "[backup] WARNING: git push FAILED — see /tmp/pushlog"
  FAIL=1
fi

# --- 2) tarball of everything irreplaceable (small files only) ---------------
mkdir -p download/backups
TAR=download/backups/milestone_${TS}.tar.gz
tar -czf /tmp/milestone_${TS}.tar.gz --exclude='*.pdf' --exclude='*.wav' \
  --exclude='*.parquet' --exclude='*.zip' --exclude='milestone_*.tar.gz' \
  plan.md worklog.md HANDOFF.md "Users note on r4 previous findings" \
  scripts/ src/ docs/ download/backups 2>/dev/null || FAIL=1
mv /tmp/milestone_${TS}.tar.gz "$TAR" 2>/dev/null || FAIL=1

# --- 3) checksum ledger -------------------------------------------------------
sha256sum "$TAR" >> download/backups/LEDGER.sha256
KEYS=$(grep -c . download/backups/LEDGER.sha256)

# --- 4) worklog append ---------------------------------------------------------
cat >> "$LOG" <<EOF

---
Task ID: BK-${TS}
Agent: backup_milestone.sh
Task: milestone backup — ${LABEL}

Work Log:
- git add/commit/push (fail=${FAIL})
- tarball ${TAR} created, ledger now ${KEYS} entries

Stage Summary:
- Milestone ${LABEL} backed up at ${TS}
EOF

# --- 5) restore-card check (key-survival) -------------------------------------
if [ ! -f download/RESTORE_CARD.md ]; then
cat > download/RESTORE_CARD.md <<'EOF'
# RESTORE CARD — read after any sandbox wipe
1. Recreate repo: `git clone https://github.com/ssmurfgg04-gif/misc-notes.git /home/z/my-project`
   (code+docs+plans come back instantly; data/ is re-downloadable per docs/data-links.md)
2. Git push token: retrieve from user (Zindi session owner). Remote format:
   `git remote set-url origin https://ssmurfgg04-gif:<TOKEN>@github.com/ssmurfgg04-gif/misc-notes.git`
   Kaggle Bearer token: `~/.kaggle/access_token` (also needs re-fetch from user).
3. Data recovery (verified SHA256SUMS in repo + misc-notes-data release v1/v3):
   - SA package: data/South_African_Real_Acoustics/ (Kaggle mirror or GH release v1)
   - Test.csv: GH release v1
   - refs/bg_refs parquets: workspace/misc-notes-data v2 (re-pull via scripts/fetch.sh)
   - VTUAD CSVs: data/zenodo_r9/ (in git; WAVs 4.6 GB optional from Zenodo 23037895)
4. Baselines that must never be re-derived:
   LB constants mu=0.13007576, E[f2]=0.06058, sigma=0.20895;
   r7_v2 map a=1.175382 gamma=6.290444; r7_v3_k045 sha 98775aed (download/submission_r7_v3_k045_PIN.csv)
5. Read HANDOFF.md + plan.md latest sections + worklog.md tail BEFORE any work.
EOF
fi
echo "[backup] DONE fail=${FAIL}"
exit $FAIL
