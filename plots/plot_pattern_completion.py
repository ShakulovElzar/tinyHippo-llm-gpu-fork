#!/usr/bin/env python3
"""
plot_pattern_completion.py
==========================
Plot the CA3 auto-association completion curve saved by
replay_scaled.py --pattern-completion (replay_output_<N>pct/pattern_completion.h5).

Intact (sup_local recurrence ON) vs ablated (sup_local = 0). A sharp
sigmoidal rise in the intact curve with the ablated curve flat at zero is the
recurrent-completion signature (Marr 1971; Nakazawa et al. 2002).

Usage:
    python plots/plot_pattern_completion.py [--in FILE] [--out FILE]
"""
import argparse
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import h5py


def load(path, group):
    with h5py.File(path, "r") as f:
        g = f[group]
        cf   = g["cue_frac"][:]
        comp = g["completion"][:]
        base = g["completion_baseline"][:]
        scale = f.attrs.get("scale", "?")
    # drop the degenerate full-cue point (NaN: nothing to complete)
    keep = ~np.isnan(comp)
    return cf[keep] * 100.0, comp[keep], base[keep], scale


def find_threshold(cue_pct, comp, level=0.5):
    """Cue % at which completion first crosses `level` (linear interp)."""
    for i in range(1, len(comp)):
        if comp[i - 1] < level <= comp[i]:
            f = (level - comp[i - 1]) / (comp[i] - comp[i - 1])
            return cue_pct[i - 1] + f * (cue_pct[i] - cue_pct[i - 1])
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp",
                    default="replay_output_1pct/pattern_completion.h5")
    ap.add_argument("--out", dest="out",
                    default="replay_output_1pct/pattern_completion.png")
    args = ap.parse_args()

    cue_i, comp_i, base_i, scale = load(args.inp, "intact")
    cue_a, comp_a, _,      _     = load(args.inp, "ablated")

    fig, ax = plt.subplots(figsize=(7.2, 5.2))

    ax.plot(cue_i, comp_i, "-o", color="#1f77b4", lw=2.2, ms=7,
            label="intact  (recurrence ON)", zorder=3)
    ax.plot(cue_a, comp_a, "--s", color="#d62728", lw=1.8, ms=6,
            label="ablated  (sup_local = 0)", zorder=3)
    ax.plot(cue_i, base_i, ":", color="grey", lw=1.2, label="pre-cue baseline")

    # unity reference (perfect completion) and the 50% threshold
    ax.axhline(1.0, color="k", lw=0.6, alpha=0.3)
    thr = find_threshold(cue_i, comp_i, 0.5)
    if thr is not None:
        ax.axvline(thr, color="#1f77b4", ls="--", lw=0.9, alpha=0.6)
        ax.annotate(f"threshold ≈ {thr:.0f}% cue",
                    xy=(thr, 0.5), xytext=(thr + 6, 0.42),
                    fontsize=9, color="#1f77b4",
                    arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=0.8))

    ax.set_xlabel("Cue size  (% of assembly directly stimulated)")
    ax.set_ylabel("Completion  (fraction of un-cued cells reactivated)")
    ax.set_title(f"CA3 pattern completion (auto-association)  —  {scale}")
    ax.set_ylim(-0.03, 1.05)
    ax.set_xlim(0, max(cue_i.max(), cue_a.max()) + 5)
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)

    ax.text(0.98, 0.03,
            "Sharp intact rise + flat ablated = recurrent completion\n"
            "(Marr 1971; Nakazawa et al. 2002)",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, color="dimgrey")

    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    fig.savefig(args.out, dpi=150)
    plt.close(fig)
    print(f">>> Saved {args.out}")


if __name__ == "__main__":
    main()
