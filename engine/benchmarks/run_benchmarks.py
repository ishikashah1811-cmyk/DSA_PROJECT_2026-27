"""Module 1 benchmark: LSH pipeline vs exact brute force (plan, Section 2.1.1).

Per configuration it reports wall-clock time of each stage, candidate count C
versus n(n-1)/2, recall (and precision in fast mode) against the brute-force
ground truth, and precision / recall / F1 against the planted duplicate pairs.
Every timing is labeled by implementation (pure Python or numpy).

    cd engine
    python benchmarks/run_benchmarks.py                                  # scaling test
    python benchmarks/run_benchmarks.py --sizes 2000 --sweep br          # (b, r) from the plan's table
    python benchmarks/run_benchmarks.py --sizes 2000 --sweep shingle     # char vs word shingles (F1)
    python benchmarks/run_benchmarks.py --sizes 2000 --sweep threshold   # t in --thresholds
    python benchmarks/run_benchmarks.py --verify fast --check-collisions
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

ENGINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from synthetic import SyntheticDataGenerator, read_captions  # noqa: E402
from evaluation import expand_to_captions, label_scores, ordered, pair_scores  # noqa: E402

from contentiq_engine.dedupe import BruteForceDetector, LSHIndex, MinHasher, group_exact_duplicates, jaccard  # noqa: E402
from contentiq_engine.text import Preprocessor, Shingler, make_shingler, shingle_corpus, stable_hash32  # noqa: E402

BR_CONFIGS = [(8, 16), (16, 8), (32, 4), (64, 2)]
SHINGLE_CONFIGS = [("char", 4), ("char", 5), ("char", 6), ("word", 2), ("word", 3)]
DEFAULT_MIN_SHINGLES = {"char": 10, "word": 3}


@dataclass
class Corpus:
    """Captions after preprocessing, the exact-duplicate pre-pass and flagging."""

    sets: list[set[int]]  # shingle IDs, one per compared document
    doc_caption: list[int]  # compared document -> caption index
    members: dict[int, list[int]]  # representative caption -> all captions identical to it
    exact_groups: list[list[int]]
    n_flagged: int
    str_sets: list[set[str]] | None  # string shingles, only kept for --check-collisions


@dataclass
class Row:
    seed: int
    n: int
    n_compared: int  # after exact-duplicate pre-pass and short-caption flagging
    n_flagged: int
    n_exact_groups: int
    shingle: str
    min_shingles: int
    bands: int
    rows: int
    threshold: float
    verify: str  # exact: Jaccard on shingle sets; fast: MinHash estimate
    prep_ms: float  # preprocess + exact pre-pass + shingling (pure Python)
    signature_ms: float  # MinHash signatures (numpy)
    lsh_ms: float  # banding + candidate generation (pure Python dicts)
    verify_ms: float  # verification of candidates (pure Python / numpy per pair)
    lsh_total_ms: float  # signature + lsh + verify
    n_candidates: int
    all_pairs: int
    lsh_pairs: int
    brute_ms: float | None  # exact all-pairs Jaccard (pure Python)
    brute_sig_ms: float | None  # all-pairs signature comparison (numpy)
    brute_pairs: int | None
    recall: float | None  # vs brute force
    precision: float | None  # vs brute force; 1.0 by construction in exact mode
    label_precision: float  # vs planted pairs, caption level
    label_recall: float
    label_f1: float
    id_collisions: int | None  # distinct shingle strings sharing a 32-bit ID
    max_jaccard_diff: float | None  # max |J(ids) - J(strings)| over candidate pairs


def ms_since(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)


def prepare(captions: list[str], shingler: Shingler, min_shingles: int, keep_strings: bool) -> tuple[Corpus, float]:
    t0 = time.perf_counter()
    pre = Preprocessor()
    normalized = [pre(c) for c in captions]
    exact = group_exact_duplicates(normalized)
    members = {rep: [rep] for rep in exact.representatives}
    for group in exact.groups:
        members[group[0]] = group
    rep_texts = [normalized[i] for i in exact.representatives]
    sets, flagged = shingle_corpus(rep_texts, shingler, min_shingles)
    flagged_set = set(flagged)
    keep = [i for i in range(len(sets)) if i not in flagged_set]
    corpus = Corpus(
        sets=[sets[i] for i in keep],
        doc_caption=[exact.representatives[i] for i in keep],
        members=members,
        exact_groups=exact.groups,
        n_flagged=len(flagged),
        str_sets=[shingler.shingles(rep_texts[i]) for i in keep] if keep_strings else None,
    )
    return corpus, ms_since(t0)


def collision_stats(corpus: Corpus, pairs: set[tuple[int, int]]) -> tuple[int, float]:
    strings = set().union(*corpus.str_sets) if corpus.str_sets else set()
    collisions = len(strings) - len({stable_hash32(s) for s in strings})
    max_diff = max(
        (abs(jaccard(corpus.sets[a], corpus.sets[b]) - jaccard(corpus.str_sets[a], corpus.str_sets[b])) for a, b in pairs),
        default=0.0,
    )
    return collisions, round(max_diff, 6)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sizes", type=int, nargs="+", default=[500, 1000, 2000, 5000])
    p.add_argument("--sweep", choices=["none", "br", "shingle", "threshold"], default="none")
    p.add_argument("--shingle", choices=["char", "word"], default="char")
    p.add_argument("--k", type=int, default=None, help="shingle size (default: 4 for char, 2 for word)")
    p.add_argument("--bands", type=int, default=32)
    p.add_argument("--rows", type=int, default=4)
    p.add_argument("--threshold", type=float, default=0.6)
    p.add_argument("--thresholds", type=float, nargs="+", default=[0.4, 0.5, 0.6, 0.7, 0.8])
    p.add_argument("--verify", choices=["exact", "fast"], default="exact")
    p.add_argument("--min-shingles", type=int, default=None, help="default: 10 for char, 3 for word shingles")
    p.add_argument("--bucket-cap", type=int, default=None)
    p.add_argument("--brute-max-n", type=int, default=5000, help="skip brute force above this n (it is O(n^2))")
    p.add_argument("--check-collisions", action="store_true", help="compare Jaccard on 32-bit IDs vs string shingles")
    p.add_argument("--dup-fraction", type=float, default=0.15)
    p.add_argument("--max-edit-rate", type=float, default=0.3)
    p.add_argument("--base-captions", type=Path, default=None, help="real captions (CSV with a caption column, or .txt)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=ENGINE_DIR / "benchmarks" / "results" / "module1.csv")
    args = p.parse_args()

    shingle_cfgs = SHINGLE_CONFIGS if args.sweep == "shingle" else [(args.shingle, args.k)]
    br_cfgs = BR_CONFIGS if args.sweep == "br" else [(args.bands, args.rows)]
    thresholds = args.thresholds if args.sweep == "threshold" else [args.threshold]

    base = read_captions(args.base_captions) if args.base_captions else None
    results: list[Row] = []
    for n in args.sizes:
        data = SyntheticDataGenerator(args.seed, base).generate(n, args.dup_fraction, args.max_edit_rate)
        captions, planted = data.captions, data.planted_pairs
        run_brute = n <= args.brute_max_n
        for kind, k in shingle_cfgs:
            shingler = make_shingler(kind, k)
            min_shingles = args.min_shingles if args.min_shingles is not None else DEFAULT_MIN_SHINGLES[kind]
            corpus, prep_ms = prepare(captions, shingler, min_shingles, keep_strings=args.check_collisions)
            sets, m = corpus.sets, len(corpus.sets)
            sig_cache: dict[int, tuple[np.ndarray, float]] = {}
            brute_cache: dict[float, tuple[set, float]] = {}
            brute_sig_cache: dict[tuple[int, float], float] = {}

            for bands, rows in br_cfgs:
                h = bands * rows
                if h not in sig_cache:
                    t0 = time.perf_counter()
                    sig_cache[h] = (MinHasher(h, seed=args.seed).signatures(sets), ms_since(t0))
                sigs, signature_ms = sig_cache[h]

                t0 = time.perf_counter()
                index = LSHIndex(bands, rows, max_bucket_size=args.bucket_cap)
                index.add_many(range(m), sigs)
                candidates = index.candidate_pairs()
                lsh_ms = ms_since(t0)

                for t in thresholds:
                    t0 = time.perf_counter()
                    if args.verify == "exact":
                        found = {(a, b) for a, b in candidates if jaccard(sets[a], sets[b]) >= t}
                    else:
                        found = {(a, b) for a, b in candidates if MinHasher.estimate_jaccard(sigs[a], sigs[b]) >= t}
                    verify_ms = ms_since(t0)

                    brute_ms = brute_sig_ms = brute_pairs = recall = precision = None
                    if run_brute:
                        det = BruteForceDetector(t)
                        if t not in brute_cache:
                            t0 = time.perf_counter()
                            truth = {ordered(pr.a, pr.b) for pr in det.find_pairs(sets)}
                            brute_cache[t] = (truth, ms_since(t0))
                        if (h, t) not in brute_sig_cache:
                            t0 = time.perf_counter()
                            det.find_pairs_signatures(sigs)
                            brute_sig_cache[(h, t)] = ms_since(t0)
                        truth, brute_ms = brute_cache[t]
                        brute_sig_ms = brute_sig_cache[(h, t)]
                        brute_pairs = len(truth)
                        precision, recall = (round(x, 4) for x in pair_scores(found, truth))

                    predicted = expand_to_captions(found, corpus.doc_caption, corpus.members, corpus.exact_groups)
                    labels = label_scores(predicted, planted)
                    collisions = max_diff = None
                    if args.check_collisions:
                        collisions, max_diff = collision_stats(corpus, candidates)

                    results.append(
                        Row(
                            seed=args.seed,
                            n=n,
                            n_compared=m,
                            n_flagged=corpus.n_flagged,
                            n_exact_groups=len(corpus.exact_groups),
                            shingle=f"{kind}{shingler.k}",
                            min_shingles=min_shingles,
                            bands=bands,
                            rows=rows,
                            threshold=t,
                            verify=args.verify,
                            prep_ms=prep_ms,
                            signature_ms=signature_ms,
                            lsh_ms=lsh_ms,
                            verify_ms=verify_ms,
                            lsh_total_ms=round(signature_ms + lsh_ms + verify_ms, 1),
                            n_candidates=len(candidates),
                            all_pairs=m * (m - 1) // 2,
                            lsh_pairs=len(found),
                            brute_ms=brute_ms,
                            brute_sig_ms=brute_sig_ms,
                            brute_pairs=brute_pairs,
                            recall=recall,
                            precision=precision,
                            label_precision=round(labels.precision, 4),
                            label_recall=round(labels.recall, 4),
                            label_f1=round(labels.f1, 4),
                            id_collisions=collisions,
                            max_jaccard_diff=max_diff,
                        )
                    )
                    print(f"done n={n} {kind}{shingler.k} b={bands} r={rows} t={t}", file=sys.stderr)

    print_table(results, args.check_collisions)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0])))
        writer.writeheader()
        writer.writerows(asdict(r) for r in results)
    print(f"\nwrote {args.out}")


def print_table(rows: list[Row], collisions: bool) -> None:
    cols = ["n", "n_compared", "shingle", "bands", "rows", "threshold", "verify", "n_candidates", "all_pairs",
            "lsh_pairs", "brute_pairs", "lsh_total_ms", "brute_ms", "brute_sig_ms", "recall", "precision",
            "label_precision", "label_recall", "label_f1"]
    if collisions:
        cols += ["id_collisions", "max_jaccard_diff"]
    widths = [max(len(c), *(len(str(getattr(r, c))) for r in rows)) for c in cols]
    print("  ".join(c.rjust(w) for c, w in zip(cols, widths)))
    for r in rows:
        print("  ".join(str(getattr(r, c)).rjust(w) for c, w in zip(cols, widths)))


if __name__ == "__main__":
    main()
