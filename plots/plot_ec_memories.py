#!/usr/bin/env python3
"""EC LII spike raster for a run with --ec-memories (LLM step 3a).

One panel per memory: the first epoch that showed it. Rows are EC LII cells,
sorted by home pattern (home_group % n_patterns), so each memory's own cells form
one band. Shaded: the forward and reverse SWR windows, where the drive is on.

    python plots/plot_ec_memories.py out/em/em3_s202.h5 -o figures/em3_s202_raster.png
"""
import argparse
import textwrap

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("h5")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()

    with h5py.File(a.h5) as f:
        texts = [t.decode() if isinstance(t, bytes) else t for t in f["ec_memories/text"][:]]
        n_pat = int(f.attrs["n_patterns"])
        ep_pat = f.attrs["epoch_pattern"]
        ep_ms = float(f.attrs["epoch_ms"])
        wins = [(f.attrs["swr_fwd_start"], f.attrs["swr_fwd_stop"]),
                (f.attrs["swr_rev_start"], f.attrs["swr_rev_stop"])]
        g = f["ec_lii"]
        cell = g["spk_senders"][:] - int(g.attrs["gid_first"])
        t = g["spk_times"][:]
        pat_of = g["home_group"][:] % n_pat

    order = np.argsort(pat_of, kind="stable")
    row = np.empty_like(order)
    row[order] = np.arange(len(order))
    colors = plt.cm.tab10(np.arange(n_pat))

    fig, axes = plt.subplots(1, n_pat, figsize=(4.2 * n_pat, 5), sharey=True)
    for p, ax in zip(range(n_pat), np.atleast_1d(axes)):
        ep = int(np.flatnonzero(ep_pat == p)[0])
        t0 = ep * ep_ms
        m = (t >= t0) & (t < t0 + ep_ms)
        rel = t[m] - t0
        ax.scatter(rel, row[cell[m]], s=1.5, c=colors[pat_of[cell[m]]], lw=0)
        for lo, hi in wins:
            ax.axvspan(lo, hi, color="0.9", zorder=-1)
        ax.set_title(f"epoch {ep}: memory {p}\n" + "\n".join(textwrap.wrap(texts[p], 40)),
                     fontsize=8)
        ax.set_xlim(0, ep_ms)
        ax.set_xlabel("time in epoch (ms)")
    np.atleast_1d(axes)[0].set_ylabel("EC LII cell (sorted by home memory)")
    for p in range(n_pat):
        mid = np.mean(np.flatnonzero(pat_of[order] == p))
        np.atleast_1d(axes)[0].text(-0.02 * ep_ms, mid, str(p), color=colors[p],
                                    ha="right", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(a.out, dpi=130)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
