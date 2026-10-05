"""Reproduce every Module 1 benchmark number and figure in one command
(plan, Phase 3 exit criterion: "benchmark numbers recorded by a reproducible script").

    cd engine
    python benchmarks/report.py                    # writes ../docs/benchmarks/
    python benchmarks/report.py --quick            # smaller sizes, for a smoke test

Outputs: scaling.csv, sweep_br.csv, sweep_shingle.csv (every shingle type x
threshold x seed), sweep_threshold.csv, verify_fast.csv, collisions.csv,
lsh_curve.csv, benchmark.json (API shape for GET /api/benchmark, plan Section 5.5)
and the PNG figures. Only scaling.csv timings are measured with the machine
otherwise idle; the other experiments run in parallel and report accuracy.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE_DIR = HERE.parent
DEFAULT_OUT = ENGINE_DIR.parent / "docs" / "benchmarks"


SHINGLE_SEEDS = ["42", "1", "2", "3"]
SHINGLE_THRESHOLDS = ["0.4", "0.45", "0.5", "0.55", "0.6", "0.65"]


def command(script: str, *args: str) -> list[str]:
    return [sys.executable, str(HERE / script), *args]


def run(script: str, *args: str) -> None:
    """Run one experiment alone, so its timings are not disturbed."""
    print("$", script, " ".join(args), flush=True)
    t0 = time.perf_counter()
    subprocess.run(command(script, *args), check=True, stdout=subprocess.DEVNULL, cwd=ENGINE_DIR)
    print(f"  done in {time.perf_counter() - t0:.0f} s", flush=True)


def run_parallel(jobs: list[list[str]], workers: int) -> None:
    """Run accuracy experiments side by side; their timing columns are not reported."""
    print(f"running {len(jobs)} accuracy experiments, {workers} at a time", flush=True)
    t0 = time.perf_counter()
    pending = list(jobs)
    running: list[subprocess.Popen] = []
    while pending or running:
        while pending and len(running) < workers:
            running.append(subprocess.Popen(pending.pop(0), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                            cwd=ENGINE_DIR))
        time.sleep(0.5)
        for proc in [p for p in running if p.poll() is not None]:
            if proc.returncode:
                raise subprocess.CalledProcessError(proc.returncode, proc.args)
            running.remove(proc)
    print(f"  done in {time.perf_counter() - t0:.0f} s", flush=True)


def concat_csv(parts: list[Path], dest: Path) -> None:
    rows = [r for part in parts for r in csv.DictReader(part.open(newline=""))]
    with dest.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for part in parts:
        part.unlink()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--quick", action="store_true")
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    sizes = ["500", "1000", "2000"] if args.quick else ["500", "1000", "2000", "5000", "10000"]
    sweep_n = "1000" if args.quick else "2000"

    # Timing experiment first, alone on the machine.
    run("run_benchmarks.py", "--sizes", *sizes, "--brute-max-n", sizes[-1], "--out", str(out / "scaling.csv"))

    rb = "run_benchmarks.py"
    jobs = [
        command(rb, "--sizes", sweep_n, "--sweep", "br", "--out", str(out / "sweep_br.csv")),
        command(rb, "--sizes", sweep_n, "--sweep", "threshold", "--out", str(out / "sweep_threshold.csv")),
        command(rb, "--sizes", sweep_n, "--sweep", "threshold", "--verify", "fast", "--out", str(out / "verify_fast.csv")),
        command(rb, "--sizes", sweep_n, "--check-collisions", "--out", str(out / "collisions.csv")),
        command("lsh_curve.py", "--n", "1000" if args.quick else "3000", "--out", str(out / "lsh_curve.csv")),
    ]
    shingle_parts = []
    for seed in SHINGLE_SEEDS[:2] if args.quick else SHINGLE_SEEDS:
        for t in SHINGLE_THRESHOLDS:
            part = out / f"_shingle_{seed}_{t}.csv"
            shingle_parts.append(part)
            jobs.append(command(rb, "--sizes", sweep_n, "--sweep", "shingle", "--threshold", t, "--seed", seed,
                                "--out", str(part)))
    run_parallel(jobs, args.workers)
    concat_csv(shingle_parts, out / "sweep_shingle.csv")

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
