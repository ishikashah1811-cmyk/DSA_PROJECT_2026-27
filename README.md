# ContentIQ

A duplicate-content detection and hashtag intelligence engine for social media analytics (DSA project 2026-27).

- **Module 1:** finds near-duplicate captions using shingling, MinHash and LSH, groups them with Union-Find, and is evaluated against an exact brute-force baseline.
- **Module 2:** stores hashtags in a Trie for autocomplete and ranks them by smoothed engagement with a heap-based top-K.

Team: Anirudh Brahmi (B25EC1003), Eklavya Motghare (B25EC1015), Ishika Shah (B25EC1036).

## Repository layout

```
engine/                     DSA core (depends only on Post; never imports api/ or web/)
  contentiq_engine/
    models.py               Post
    base.py                 AnalyzerModule, AnalysisResult
    text/                   preprocessor.py, shingler.py                         (Person 1)
    dedupe/                 minhash.py, lsh.py, brute_force.py, exact.py,
                            similarity.py                                        (Person 1)
                            union_find.py, clusterer.py                          (Person 2)
                            analyzer.py                                          (Person 1/2)
    hashtags/               trie.py, max_heap.py, ranker.py, analyzer.py         (Person 3)
    service.py              AnalyticsService facade                              (Person 2)
  tests/                    pytest unit tests
  benchmarks/               run_benchmarks.py, toy_data.py (temporary), synthetic.py (Person 2)
api/                        FastAPI backend                                      (Person 2)
web/                        Next.js dashboard                                    (Person 3)
data/sample/                small anonymized CSV (committed)
data/raw/                   real exports (gitignored)
```

## Engine: setup and tests

```bash
cd engine
pip install -e ".[dev]"
pytest
```

## Module 1 benchmark

```bash
cd engine
python benchmarks/run_benchmarks.py --sizes 500 1000 2000 5000   # LSH vs brute-force scaling
python benchmarks/run_benchmarks.py --sizes 2000 --sweep-br      # every (b, r) from the plan
python benchmarks/run_benchmarks.py --help
```

Results are written to `engine/benchmarks/results/module1.csv`, which is gitignored. Every timing column is labeled with the implementation it uses: `brute_ms` is pure Python and `brute_sig_ms` is numpy. Until Person 2's SyntheticDataGenerator exists, the input data comes from `benchmarks/toy_data.py`.

## Workflow

Use one branch per feature. Each pull request is reviewed by one other team member and merged only once the tests pass.
