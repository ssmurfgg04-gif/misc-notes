#!/usr/bin/env python3
"""Shard task runner stub for shard-compute.yml.
R2 will implement real tasks: gen_v1 (mixture factory shards), feats, tournament.
"""
import argparse, json, os, time

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="noop")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=8)
    a = ap.parse_args()

    os.makedirs("output", exist_ok=True)
    out = {"task": a.task, "shard": a.shard, "of": a.of, "status": "stub-ok",
           "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
    # data presence check (asset may be absent for read-only tasks)
    for probe in ["data/South_African_Real_Acoustics", "data/Test.csv"]:
        out[probe] = os.path.isdir(probe) or os.path.isfile(probe)

    with open(f"output/shard_{a.shard}_result.json", "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out))

if __name__ == "__main__":
    main()
