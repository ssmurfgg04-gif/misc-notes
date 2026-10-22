#!/usr/bin/env python3
"""Resolve R10 rebase conflicts: keep BOTH parallel-session contributions.
Order: remote (execution hardening, pre-readout) then local (k* solve, post-readout).
Local-side renames: plan 7l->7m / 7m->7n; worklog D38->D40, D39->D41."""
import re, sys

BASE = "/home/z/my-project/"

def merge(path, mine_edits, glue_before_mine=""):
    with open(BASE + path) as f:
        t = f.read()
    pat = re.compile(r"<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> [^\n]*\n", re.S)
    n = 0
    def repl(m):
        nonlocal n
        n += 1
        remote, mine = m.group(1), m.group(2)
        for a, b in mine_edits:
            mine = mine.replace(a, b)
        return remote + "\n" + glue_before_mine + mine + "\n"
    t2 = pat.sub(repl, t)
    assert n > 0, f"no conflict markers found in {path}"
    with open(BASE + path, "w") as f:
        f.write(t2)
    print(f"{path}: {n} hunk(s) merged")

merge("HANDOFF.md", [], glue_before_mine="**(R10b — continuation, after the LB paste landed.)**\n\n")
merge("plan.md", [
    ("## 7l. R10 — LB PIN READOUT SOLVED", "## 7m. R10 — LB PIN READOUT SOLVED"),
    ("## 7m. Next actions (R10 → R11)", "## 7n. Next actions (R10 → R11)"),
])
merge("worklog.md", [
    ("**Decisions**\n- D38: r7_v2/r7_v3 chain FROZEN", "**Decisions**\n- D40: r7_v2/r7_v3 chain FROZEN"),
    ("- D39: submission order = r7_v4_kstar FIRST", "- D41: submission order = r7_v4_kstar FIRST"),
    ("plan.md §7l/§7m written", "plan.md §7m/§7n written"),
])
print("all merges done")
