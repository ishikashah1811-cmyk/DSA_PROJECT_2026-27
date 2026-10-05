"""Recall study: measured LSH candidate rate vs similarity, against theory
(plan, Section 2.1 step 5 and Section 2.1.1).

For every pair of documents with exact Jaccard >= --min-sim (found by brute force),
record whether LSH made it a candidate. Grouped into similarity bins, the measured
candidate rate should follow P(candidate) = 1 - (1 - s^r)^b for each (b, r).

    cd engine
    python benchmarks/lsh_curve.py --n 3000 --out benchmarks/results/lsh_curve.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_benchmarks import BR_CONFIGS, prepare  # noqa: E402
from synthetic import SyntheticDataGenerator  # noqa: E402

from contentiq_engine.dedupe import BruteForceDetector, LSHIndex, MinHasher  # noqa: E402
from contentiq_engine.text import make_shingler  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--n", type=int, default=3000)
    p.add_argument("--min-sim", type=float, default=0.2)
    p.add_argument("--bin-width", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=ENGINE_DIR / "benchmarks" / "results" / "lsh_curve.csv")
    args = p.parse_args()

    data = SyntheticDataGenerator(args.seed).generate(args.n)
    corpus, _ = prepare(data.captions, make_shingler("char", 5), 10, keep_strings=False)
    pairs = BruteForceDetector(args.min_sim).find_pairs(corpus.sets)
    print(f"{len(pairs)} pairs with Jaccard >= {args.min_sim} among {len(corpus.sets)} documents", file=sys.stderr)

    n_bins = round((1.0 - args.min_sim) / args.bin_width)
    rows = []
    for bands, rows_per_band in BR_CONFIGS:
        sigs = MinHasher(bands * rows_per_band, seed=args.seed).signatures(corpus.sets)
        index = LSHIndex(bands, rows_per_band)
        index.add_many(range(len(corpus.sets)), sigs)
        candidates = index.candidate_pairs()
        tot = [0] * n_bins
        hit = [0] * n_bins
        theory = [0.0] * n_bins
        for pr in pairs:
            k = min(int((pr.similarity - args.min_sim) / args.bin_width), n_bins - 1)
            tot[k] += 1
            hit[k] += (pr.a, pr.b) in candidates
            theory[k] += LSHIndex.candidate_probability(pr.similarity, bands, rows_per_band)
        for k in range(n_bins):
            if tot[k]:
                lo = args.min_sim + k * args.bin_width
                rows.append(
                    {
                        "bands": bands,
                        "rows": rows_per_band,
                        "bin_lo": round(lo, 3),
                        "bin_hi": round(lo + args.bin_width, 3),
                        "n_pairs": tot[k],
                        "measured": round(hit[k] / tot[k], 4),
                        "theory": round(theory[k] / tot[k], 4),  # mean of P(candidate) over the bin's pairs
                    }
                )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    worst = max(abs(r["measured"] - r["theory"]) for r in rows if r["n_pairs"] >= 30)
    print(f"wrote {args.out}; largest |measured - theory| over bins with >= 30 pairs: {worst:.3f}")


if __name__ == "__main__":
    main()
