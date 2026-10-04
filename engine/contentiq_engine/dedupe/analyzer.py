"""DuplicateAnalyzer: the full Module 1 pipeline as an AnalyzerModule
(plan, Sections 2.1 and 2.3).

preprocess -> exact-duplicate pre-pass -> shingle (flag short captions)
-> MinHash -> LSH candidates -> verify -> Union-Find clusters -> report
"""

from __future__ import annotations

import time
from typing import Any

from ..base import AnalysisResult, AnalyzerModule
from ..models import Post
from ..text import Preprocessor, make_shingler, shingle_corpus
from .clusterer import DuplicateClusterer
from .exact import group_exact_duplicates
from .lsh import LSHIndex
from .minhash import MinHasher
from .similarity import SimilarPair

DEFAULT_PARAMS: dict[str, Any] = {
    "shingle_type": "char",
    "k": 5,
    "num_hashes": 128,
    "bands": 32,
    "rows": 4,
    "threshold": 0.6,
    "min_shingles": 10,
    "verify": "exact",
    "bucket_cap": None,
    "seed": 42,
}


class DuplicateAnalyzer(AnalyzerModule):
    name = "duplicates"

    def __init__(self, preprocessor: Preprocessor | None = None) -> None:
        self.preprocessor = preprocessor or Preprocessor()
        self._posts: list[Post] = []

    def ingest(self, posts: list[Post]) -> None:
        self._posts = list(posts)

    def run(self, **params: Any) -> AnalysisResult:
        unknown = set(params) - set(DEFAULT_PARAMS)
        if unknown:
            raise ValueError(f"unknown parameters: {sorted(unknown)}")
        p = {**DEFAULT_PARAMS, **params}
        if p["bands"] * p["rows"] != p["num_hashes"]:
            raise ValueError("bands * rows must equal num_hashes")

        t0 = time.perf_counter()
        posts = self._posts
        n = len(posts)

        # 1-2. Normalize; identical captions are grouped and only one representative goes on.
        normalized = [self.preprocessor(post.caption) for post in posts]
        exact = group_exact_duplicates(normalized)

        # 3. Shingle the representatives; captions with too few shingles are flagged, not clustered.
        shingler = make_shingler(p["shingle_type"], p["k"])
        rep_sets, rep_flagged = shingle_corpus(
            [normalized[i] for i in exact.representatives], shingler, p["min_shingles"]
        )
        rep_flagged_set = set(rep_flagged)
        flagged_reps = {exact.representatives[i] for i in rep_flagged}
        keep = [i for i in range(len(rep_sets)) if i not in rep_flagged_set]
        doc_post = [exact.representatives[i] for i in keep]  # compared document -> post index
        sets = [rep_sets[i] for i in keep]

        # 4-6. MinHash signatures, LSH candidates, verification.
        signatures = MinHasher(p["num_hashes"], p["seed"]).signatures(sets)
        index = LSHIndex(p["bands"], p["rows"], max_bucket_size=p["bucket_cap"])
        index.add_many(range(len(sets)), signatures)
        candidates = index.candidate_pairs()
        clusterer = DuplicateClusterer(p["threshold"], p["verify"])
        verified = clusterer.verify(candidates, sets, signatures)

        # 7. Union-Find over all posts: verified pairs plus exact-duplicate groups (similarity 1.0).
        edges = [SimilarPair(doc_post[e.a], doc_post[e.b], e.similarity) for e in verified]
        for group in exact.groups:
            if group[0] not in flagged_reps:
                edges.extend(SimilarPair(group[0], member, 1.0) for member in group[1:])
        clusters = clusterer.cluster(n, edges)

        # 8. Report.
        members = {group[0]: group for group in exact.groups}
        flagged_posts = sorted(i for rep in flagged_reps for i in members.get(rep, [rep]))
        data = {
            "n_posts": n,
            "n_compared": len(sets),
            "n_flagged": len(flagged_posts),
            "flagged_post_ids": [posts[i].id for i in flagged_posts],
            "n_exact_groups": len(exact.groups),
            "n_candidates": len(candidates),
            "n_pairs": len(verified),
            "n_clusters": len(clusters),
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "size": c.size,
                    "post_ids": [posts[i].id for i in c.members],
                    "representative_id": posts[c.representative].id,
                    "representative_caption": posts[c.representative].caption,
                    "min_sim": round(c.min_sim, 4),
                    "avg_sim": round(c.avg_sim, 4),
                }
                for c in clusters
            ],
        }
        runtime_ms = (time.perf_counter() - t0) * 1000
        return AnalysisResult(self.name, p, data, round(runtime_ms, 1))
