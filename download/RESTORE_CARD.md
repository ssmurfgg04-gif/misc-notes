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
