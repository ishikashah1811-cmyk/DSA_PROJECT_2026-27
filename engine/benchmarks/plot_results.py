"""Figures for the Module 1 report from the CSVs written by report.py.

Static PNGs for the written report: light surface, one y-axis per chart, thin
lines with ring-outlined markers, a legend plus direct labels for every series.

    python benchmarks/plot_results.py --dir ../docs/benchmarks
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # validated categorical order (light)
MARKERS = ["o", "s", "^", "D"]

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": TEXT_2,
        "axes.titlecolor": TEXT,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": TEXT_2,
        "ytick.color": TEXT_2,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "legend.labelcolor": TEXT,
        "font.size": 10,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
    }
)


def read(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def num(v: str) -> float | None:
    return None if v in ("", "None") else float(v)


def legend_below(ax, ncol: int) -> None:
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=ncol, fontsize=9)


def line(ax, xs, ys, i, label, end_label: str | None = None, **kw):
    pts = [(x, y) for x, y in zip(xs, ys) if y is not None]
    if not pts:
        return
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=SERIES[i], lw=1.5, marker=MARKERS[i], ms=6, mec=SURFACE, mew=1.5, label=label, **kw)
    if end_label:
        ax.annotate(end_label, (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points", va="center",
                    color=TEXT, fontsize=9, gid="end_label")


def spread_end_labels(ax, min_gap_pt: float = 12) -> None:
    """Nudge end-of-line labels vertically so that none overlap."""
    fig = ax.figure
    fig.canvas.draw()
    labels = [t for t in ax.texts if t.get_gid() == "end_label"]
    to_pt = 72 / fig.dpi
    ys = [ax.transData.transform(t.xy)[1] * to_pt for t in labels]
    order = sorted(range(len(labels)), key=lambda i: ys[i])
    placed: list[float] = []
    for i in order:
        y = ys[i] if not placed else max(ys[i], placed[-1] + min_gap_pt)
        placed.append(y)
        labels[i].set_position((6, y - ys[i]))


def fig_runtime(rows: list[dict], out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ns = [int(r["n"]) for r in rows]
    line(ax, ns, [num(r["brute_ms"]) for r in rows], 0, "Brute force, exact Jaccard (pure Python)", "Brute force (Python)")
    line(ax, ns, [num(r["brute_sig_ms"]) for r in rows], 1, "Brute force, signatures (numpy)", "Brute force (numpy)")
    line(ax, ns, [num(r["lsh_total_ms"]) for r in rows], 2, "LSH pipeline (MinHash + LSH + verify)", "LSH pipeline")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Posts (n)")
    ax.set_ylabel("Wall-clock time (ms, log scale)")
    ax.set_title("Runtime: LSH pipeline vs brute force")
    ax.set_xticks(ns, [f"{n:,}" for n in ns])
    ax.minorticks_off()
    legend_below(ax, 2)
    ax.set_xlim(right=max(ns) * 3)
    spread_end_labels(ax)
    fig.savefig(out)
    plt.close(fig)


def fig_candidates(rows: list[dict], out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ns = [int(r["n"]) for r in rows]
    line(ax, ns, [num(r["all_pairs"]) for r in rows], 0, "All pairs, n(n-1)/2 (brute force)", "All pairs")
    line(ax, ns, [num(r["n_candidates"]) for r in rows], 1, "LSH candidate pairs (C)", "LSH candidates")
    line(ax, ns, [num(r["brute_pairs"]) for r in rows], 2, "True pairs (Jaccard >= t)", "True pairs")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Posts (n)")
    ax.set_ylabel("Pairs (log scale)")
    ax.set_title("Pairs compared: brute force vs LSH")
    ax.set_xticks(ns, [f"{n:,}" for n in ns])
    ax.minorticks_off()
    legend_below(ax, 3)
    ax.set_xlim(right=max(ns) * 2.5)
    spread_end_labels(ax)
    fig.savefig(out)
    plt.close(fig)


def fig_lsh_curve(rows: list[dict], out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    by_cfg: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for r in rows:
        by_cfg[(int(r["bands"]), int(r["rows"]))].append(r)
    for i, ((b, r), pts) in enumerate(sorted(by_cfg.items())):
        mids = [(float(p["bin_lo"]) + float(p["bin_hi"])) / 2 for p in pts]
        ax.plot(mids, [float(p["theory"]) for p in pts], color=SERIES[i], lw=1, ls="--")
        line(ax, mids, [float(p["measured"]) for p in pts], i, f"b={b}, r={r}")
        # Label each curve just left of where it crosses 0.5 (b=64 never does: label its plateau).
        k = min(range(len(pts)), key=lambda j: abs(float(pts[j]["measured"]) - 0.5))
        y = float(pts[k]["measured"])
        ax.annotate(f"b={b}, r={r}", (mids[k], y), xytext=(-10, 0), textcoords="offset points",
                    ha="right", va="center", color=TEXT, fontsize=9,
                    bbox={"boxstyle": "round,pad=0.15", "fc": SURFACE, "ec": "none"})
    ax.plot([], [], color=TEXT_2, lw=1, ls="--", label="theory 1-(1-s^r)^b")
    ax.set_xlabel("Exact Jaccard similarity of the pair (bin midpoint)")
    ax.set_ylabel("Share of pairs that became candidates")
    ax.set_title("LSH candidate rate vs similarity: measured (markers) and theory (dashed)")
    ax.set_ylim(-0.03, 1.08)
    ax.set_xlim(0.1, 1.0)
    legend_below(ax, 5)
    fig.savefig(out)
    plt.close(fig)


def fig_bar(labels: list[str], values: list[float], title: str, ylabel: str, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    bars = ax.bar(labels, values, color=SERIES[0], width=0.6, edgecolor=SURFACE, linewidth=2)
    for bar, v in zip(bars, values):
        ax.annotate(f"{v:.3f}", (bar.get_x() + bar.get_width() / 2, v), xytext=(0, 3),
                    textcoords="offset points", ha="center", color=TEXT, fontsize=9)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="x", visible=False)
    fig.savefig(out)
    plt.close(fig)


def best_shingle_settings(rows: list[dict]) -> list[dict]:
    """Per shingle type, the threshold with the best mean F1 over seeds."""
    groups: dict[tuple[str, float], list[float]] = defaultdict(list)
    for r in rows:
        groups[(r["shingle"], float(r["threshold"]))].append(float(r["label_f1"]))
    best: dict[str, dict] = {}
    for (shingle, t), f1s in groups.items():
        mean = sum(f1s) / len(f1s)
        if shingle not in best or mean > best[shingle]["mean"]:
            best[shingle] = {"shingle": shingle, "threshold": t, "mean": mean, "min": min(f1s), "max": max(f1s),
                             "seeds": len(f1s)}
    order = [r["shingle"] for r in rows]
    return sorted(best.values(), key=lambda b: order.index(b["shingle"]))


def fig_shingle(rows: list[dict], out: Path) -> None:
    best = best_shingle_settings(rows)
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    xs = [b["shingle"] for b in best]
    means = [b["mean"] for b in best]
    err = [[m - b["min"] for m, b in zip(means, best)], [b["max"] - m for m, b in zip(means, best)]]
    bars = ax.bar(xs, means, color=SERIES[0], width=0.6, edgecolor=SURFACE, linewidth=2)
    ax.errorbar(xs, means, yerr=err, fmt="none", ecolor=TEXT_2, elinewidth=1, capsize=4)
    for bar, b in zip(bars, best):
        ax.annotate(f"{b['mean']:.3f}\nt={b['threshold']:g}", (bar.get_x() + bar.get_width() / 2, b["max"]),
                    xytext=(0, 4), textcoords="offset points", ha="center", color=TEXT, fontsize=9)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel(f"F1 (mean of {best[0]['seeds']} seeds, range bars)")
    ax.set_title("Shingle type at its best threshold: F1 against planted duplicates")
    ax.grid(axis="x", visible=False)
    fig.savefig(out)
    plt.close(fig)


def fig_threshold(rows: list[dict], out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    ts = [float(r["threshold"]) for r in rows]
    line(ax, ts, [float(r["label_precision"]) for r in rows], 0, "Precision", "Precision")
    line(ax, ts, [float(r["label_recall"]) for r in rows], 1, "Recall", "Recall")
    line(ax, ts, [float(r["label_f1"]) for r in rows], 2, "F1", "F1")
    ax.set_xlabel("Verification threshold t")
    ax.set_ylabel("Score vs planted duplicates")
    ax.set_title(f"Choosing the threshold t ({rows[0]['shingle']} shingles, b=32, r=4)")
    ax.set_ylim(0, 1.05)
    ax.set_xlim(min(ts) - 0.03, max(ts) + 0.1)
    legend_below(ax, 3)
    spread_end_labels(ax)
    fig.savefig(out)
    plt.close(fig)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dir", type=Path, required=True, help="folder with the CSVs; figures are written there")
    args = p.parse_args()
    d = args.dir
    fig_runtime(read(d / "scaling.csv"), d / "runtime.png")
    fig_candidates(read(d / "scaling.csv"), d / "candidates.png")
    fig_lsh_curve(read(d / "lsh_curve.csv"), d / "lsh_curve.png")
    fig_shingle(read(d / "sweep_shingle.csv"), d / "shingle_f1.png")
    br = read(d / "sweep_br.csv")
    fig_bar([f"b={r['bands']}, r={r['rows']}" for r in br], [float(r["recall"]) for r in br],
            "(b, r): recall against brute force at t = 0.6", "Recall", d / "br_recall.png")
    fig_threshold(read(d / "sweep_threshold.csv"), d / "threshold.png")
    print(f"wrote figures to {d}")


if __name__ == "__main__":
    main()
