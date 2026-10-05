"""Reproduce every Module 1 benchmark number and figure in one command
(plan, Phase 3 exit criterion: "benchmark numbers recorded by a reproducible script").

    cd engine
    python benchmarks/report.py                    # writes ../docs/benchmarks/
    python benchmarks/report.py --quick            # smaller sizes, for a smoke test

Outputs: scaling.csv, sweep_br.csv, sweep_shingle.csv, sweep_threshold.csv,
verify_fast.csv, collisions.csv, lsh_curve.csv, benchmark.json (API shape for
GET /api/benchmark, plan Section 5.5) and the PNG figures.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE_DIR = HERE.parent
DEFAULT_OUT = ENGINE_DIR.parent / "docs" / "benchmarks"


def run(script: str, *args: str) -> None:
    cmd = [sys.executable, str(HERE / script), *args]
    print("$", " ".join(cmd[1:]), flush=True)
    t0 = time.perf_counter()
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, cwd=ENGINE_DIR)
    print(f"  done in {time.perf_counter() - t0:.0f} s", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--quick", action="store_true")
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    sizes = ["500", "1000", "2000"] if args.quick else ["500", "1000", "2000", "5000", "10000"]
    sweep_n = "1000" if args.quick else "2000"
    brute_max = sizes[-1]

    run("run_benchmarks.py", "--sizes", *sizes, "--brute-max-n", brute_max, "--out", str(out / "scaling.csv"))
    run("run_benchmarks.py", "--sizes", sweep_n, "--sweep", "br", "--out", str(out / "sweep_br.csv"))
    run("run_benchmarks.py", "--sizes", sweep_n, "--sweep", "shingle", "--out", str(out / "sweep_shingle.csv"))
    run("run_benchmarks.py", "--sizes", sweep_n, "--sweep", "threshold", "--out", str(out / "sweep_threshold.csv"))
    run("run_benchmarks.py", "--sizes", sweep_n, "--sweep", "threshold", "--verify", "fast",
        "--out", str(out / "verify_fast.csv"))
    run("run_benchmarks.py", "--sizes", sweep_n, "--check-collisions", "--out", str(out / "collisions.csv"))
    run("lsh_curve.py", "--n", "1000" if args.quick else "3000", "--out", str(out / "lsh_curve.csv"))

    with (out / "scaling.csv").open(newline="") as f:
        api = [
            {
                "n": int(r["n"]),
                "brute_ms": None if r["brute_ms"] in ("", "None") else float(r["brute_ms"]),
                "lsh_ms": float(r["lsh_total_ms"]),
                "recall": None if r["recall"] in ("", "None") else float(r["recall"]),
                "candidates": int(r["n_candidates"]),
            }
            for r in csv.DictReader(f)
        ]
    (out / "benchmark.json").write_text(json.dumps(api, indent=2) + "\n")

    run("plot_results.py", "--dir", str(out))
    print(f"all results in {out}")


if __name__ == "__main__":
    main()
