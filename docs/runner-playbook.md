# runner-playbook.md — free compute: GitHub runners + Kaggle GPU

## GitHub Actions (public repo = $0, unlimited standard-runner minutes)
- `ubuntu-latest`: 4 vCPU, 16 GB RAM, ~14 GB free SSD. **6 h hard cap per job** — shard everything.
- Parallelism: `strategy.matrix` with N shards; each shard writes an artifact; a final `aggregate` job (`needs: [shards]`) merges.
- Limits: artifact retention ≤ 90 days (set 30), cache 10 GB/repo, concurrent jobs free-tier ≈ 20.
- Concurrency guard in every workflow (below) — avoids queue pileups.

### Workflow template (sharded compute)
```yaml
name: shard-compute
on:
  workflow_dispatch:
    inputs: { shards: {default: "8"}, task: {default: "gen_v1"} }
concurrency: { group: shard-compute, cancel-in-progress: true }
jobs:
  shard:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix: { shard: [0,1,2,3,4,5,6,7] }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements.txt
      - name: pull data (private backup repo release asset)
        env: { GH_PAT: "${{ secrets.GH_PAT }}" }
        run: |
          curl -sL -H "Authorization: Bearer $GH_PAT" \
            -o data.zip "https://github.com/OWNER/misc-notes-data/releases/download/v1/sa_acoustics.zip"
          unzip -q data.zip
      - run: python src/task.py --task "${{ inputs.task }}" --shard "${{ matrix.shard }}" --of "${{ inputs.shards }}"
      - uses: actions/upload-artifact@v4
        with: { name: "out-${{ matrix.shard }}", path: output/ , retention-days: 30 }
  aggregate:
    needs: [shard]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with: { pattern: "out-*", merge-multiple: true, path: output/ }
      - run: python src/aggregate.py --dir output/
      - uses: actions/upload-artifact@v4
        with: { name: aggregated, path: output/aggregated.* }
```

### Secrets to set on `misc-notes` (user action, Settings → Secrets → Actions)
- `GH_PAT` — the PAT in use (repo scope) for pulling the private data repo
- `KAGGLE_API_TOKEN` — for Kaggle GPU handoff + dataset pull
- never `echo` secrets; never interpolate into `run:` strings unquoted

## Kaggle GPU ($0, token configured)
- Quota: ~30 GPU h/week, 12 h max/session; P100 (16 GB) or T4×2.
- Auth quirk: CLI 2.2.4 ignores `KAGGLE_API_TOKEN` env in some flows — use
  direct REST (`Authorization: Bearer $KAGGLE_API_TOKEN`) or write the token to
  `~/.kaggle/access_token` + `kaggle auth login` fallback. Verified working:
  `curl -H "Authorization: Bearer $TOKEN" https://www.kaggle.com/api/v1/...`
- Data into notebooks: private Kaggle Dataset (upload from here) or private
  GitHub release asset fetched inside the notebook.
- Handoff pattern: notebooks pull data → train → push results as Kaggle
  dataset version → mirror result artifact into `misc-notes` via API commit.

## When to use which
| Task | Where |
|---|---|
| feature build / generator shards / tournament a–c (LightGBM) | GH Actions matrix (4c/16 GB plenty) |
| small CNN two-head training | Kaggle P100 |
| write-up figures / pressure maps | local |
