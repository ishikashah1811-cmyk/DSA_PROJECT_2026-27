"""Module 1 benchmark: LSH pipeline vs exact brute force (plan, Section 2.1.1).

Reports, per corpus size n: wall-clock time of each stage, candidate count C
versus n(n-1)/2, and recall of LSH against the brute-force ground truth.
Every timing is labeled by implementation (pure Python or numpy).

    cd engine
    python benchmarks/run_benchmarks.py                         # scaling test
    python benchmarks/run_benchmarks.py --sweep-br --sizes 2000 # (b, r) sweep
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import toy_data  # noqa: E402

from contentiq_engine.dedupe import BruteForceDetector, LSHIndex, MinHasher, group_exact_duplicates, jaccard  # noqa: E402
from contentiq_engine.text import Preprocessor, make_shingler, shingle_corpus  # noqa: E402

BR_CONFIGS = [(8, 16), (16, 8), (32, 4), (64, 2)]


@dataclass
class Row:
    n: int
    n_compared: int  # after exact-duplicate pre-pass and short-caption flagging
    n_flagged: int
    n_exact_groups: int
    shingle_type: str
    k: int
    bands: int
    rows: int
    threshold: float
    prep_ms: float  # preprocess + exact pre-pass + shingling (pure Python)
    signature_ms: float  # MinHash signatures (numpy)
    lsh_ms: float  # banding + candidate generation (pure Python dicts)
    verify_ms: float  # exact Jaccard on candidates (pure Python)
    n_candidates: int
    all_pairs: int
    lsh_pairs: int
    brute_ms: float | None  # exact all-pairs Jaccard (pure Python)
    brute_sig_ms: float | None  # all-pairs signature comparison (numpy)
    brute_pairs: int | None
    recall: float | None


def ms_since(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000


def run_once(captions, args, bands, rows, run_brute) -> Row:
    t0 = time.perf_counter()
    pre = Preprocessor()
    normalized = [pre(c) for c in captions]
    exact = group_exact_duplicates(normalized)
    shingler = make_shingler(args.shingle, args.k)
    sets, flagged = shingle_corpus([normalized[i] for i in exact.representatives], shingler, args.min_shingles)
    flagged_set = set(flagged)
    keep = [i for i in range(len(sets)) if i not in flagged_set]
    sets = [sets[i] for i in keep]
    prep_ms = ms_since(t0)

    t0 = time.perf_counter()
    sigs = MinHasher(bands * rows, seed=args.seed).signatures(sets)
    signature_ms = ms_since(t0)

    t0 = time.perf_counter()
    index = LSHIndex(bands, rows, max_bucket_size=args.bucket_cap)
    index.add_many(range(len(sets)), sigs)
    candidates = index.candidate_pairs()
    lsh_ms = ms_since(t0)

    t0 = time.perf_counter()
    lsh_found = {(a, b) for a, b in candidates if jaccard(sets[a], sets[b]) >= args.threshold}
    verify_ms = ms_since(t0)

    m = len(sets)
    brute_ms = brute_sig_ms = brute_pairs = recall = None
    if run_brute:
        det = BruteForceDetector(args.threshold)
        t0 = time.perf_counter()
        truth = {(p.a, p.b) for p in det.find_pairs(sets)}
        brute_ms = ms_since(t0)
        t0 = time.perf_counter()
        det.find_pairs_signatures(sigs)
        brute_sig_ms = ms_since(t0)
        brute_pairs = len(truth)
        recall = len(lsh_found & truth) / len(truth) if truth else 1.0

    return Row(
        n=len(captions),
        n_compared=m,
        n_flagged=len(flagged),
        n_exact_groups=len(exact.groups),
        shingle_type=args.shingle,
        k=shingler.k,
        bands=bands,
        rows=rows,
        threshold=args.threshold,
        prep_ms=round(prep_ms, 1),
        signature_ms=round(signature_ms, 1),
        lsh_ms=round(lsh_ms, 1),
        verify_ms=round(verify_ms, 1),
        n_candidates=len(candidates),
        all_pairs=m * (m - 1) // 2,
        lsh_pairs=len(lsh_found),
        brute_ms=None if brute_ms is None else round(brute_ms, 1),
        brute_sig_ms=None if brute_sig_ms is None else round(brute_sig_ms, 1),
        brute_pairs=brute_pairs,
        recall=None if recall is None else round(recall, 4),
    )


def print_table(rows: list[Row]) -> None:
    cols = ["n", "n_compared", "bands", "rows", "signature_ms", "lsh_ms", "verify_ms",
            "n_candidates", "all_pairs", "lsh_pairs", "brute_pairs", "brute_ms", "brute_sig_ms", "recall"]
    widths = [max(len(c), *(len(str(getattr(r, c))) for r in rows)) for c in cols]
    print("  ".join(c.rjust(w) for c, w in zip(cols, widths)))
    for r in rows:
        print("  ".join(str(getattr(r, c)).rjust(w) for c, w in zip(cols, widths)))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sizes", type=int, nargs="+", default=[500, 1000, 2000, 5000])
    p.add_argument("--shingle", choices=["char", "word"], default="char")
    p.add_argument("--k", type=int, default=None, help="shingle size (default: 5 for char, 2 for word)")
    p.add_argument("--bands", type=int, default=32)
    p.add_argument("--rows", type=int, default=4)
    p.add_argument("--sweep-br", action="store_true", help="run every (b, r) from the plan's table")
    p.add_argument("--threshold", type=float, default=0.6)
    p.add_argument("--min-shingles", type=int, default=10)
    p.add_argument("--bucket-cap", type=int, default=None)
    p.add_argument("--brute-max-n", type=int, default=5000, help="skip brute force above this n (it is O(n^2))")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=ENGINE_DIR / "benchmarks" / "results" / "module1.csv")
    args = p.parse_args()

    configs = BR_CONFIGS if args.sweep_br else [(args.bands, args.rows)]
    results: list[Row] = []
    for n in args.sizes:
        captions, _planted = toy_data.generate(n, seed=args.seed)
        for bands, rows in configs:
            row = run_once(captions, args, bands, rows, run_brute=n <= args.brute_max_n)
            results.append(row)
            print(f"done n={n} b={bands} r={rows}", file=sys.stderr)

    print_table(results)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0])))
        writer.writeheader()
        writer.writerows(asdict(r) for r in results)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
