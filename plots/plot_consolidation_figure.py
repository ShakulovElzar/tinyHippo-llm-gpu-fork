#!/usr/bin/env python3
"""
plot_consolidation_figure.py
============================
Six-panel summary of the three core phenomena, straight from a replay_scaled.py
HDF5 file:

  A/B  bidirectional replay  — CA3 sequence-group heatmaps for the forward and
                               reverse SWR windows (the diagonal is the replay)
  C    replay quality        — Spearman rho per direction, scored on the SWR
                               window (see replay_score docstring)
  D    synaptic tagging      — tagged synapses and PRP accumulation per SWR event
  E    consolidation         — L-LTP staircase and mean CA1->EC weight
  F    engram               — final weight distribution (bimodal = consolidated)

Usage:
    python plots/plot_consolidation_figure.py [--in FILE] [--out FILE]
"""
import argparse
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import h5py

C_FWD, C_REV, C_TAG, C_LTP, C_W = "#1f77b4", "#d62728", "#9467bd", "#e08214", "#2e7d5b"


def heat_panel(ax, H, times, win, title, colour):
    a, b = win
    sel = (times >= a - 20) & (times <= b + 20)
    im = ax.imshow(H[:, sel], aspect="auto", origin="lower", cmap="magma",
                   extent=[times[sel][0], times[sel][-1], 0, H.shape[0]])
    ax.axvline(a, color="w", ls="--", lw=0.8, alpha=0.7)
    ax.axvline(b, color="w", ls="--", lw=0.8, alpha=0.7)
    ax.set_xlabel("time (ms)")
    ax.set_ylabel("CA3 sequence group")
    ax.set_title(title, fontsize=10, loc="left", color=colour, fontweight="bold")
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp",
                    default="res/2026-08-05/replay_12pct_stc_dg_lv_mpfc.h5")
    ap.add_argument("--out", dest="out", default="figures/consolidation_overview.png")
    args = ap.parse_args()

    from scipy.stats import spearmanr

    def score(t, s, groups, a, b):
        """Recompute rho on the SWR window from raw spikes.

        Deliberately NOT read from /stats: files written before the scoring-window
        fix stored rho for the padded window (start-5, stop+30), whose post-SWR
        rebound cancels the reverse direction (-0.094 stored vs -0.789 actual).
        """
        m = (t >= a) & (t <= b)
        tw, sw = t[m], s[m]
        gi, gv = [], []
        for k, grp in enumerate(groups):
            tg = tw[np.isin(sw, grp)]
            if len(tg) >= 3:
                gi.append(k); gv.append(tg.mean())
        if len(gi) < 4:
            return float("nan"), float("nan")
        r, p = spearmanr(gi, gv)
        return float(r), float(p)

    with h5py.File(args.inp, "r") as f:
        H      = f["ca3_sup"]["heatmap"][:]
        times  = f["times_ms"][:]
        scale  = f.attrs.get("scale", "?")
        fwd    = (float(f.attrs["swr_fwd_start"]), float(f.attrs["swr_fwd_stop"]))
        rev    = (float(f.attrs["swr_rev_start"]), float(f.attrs["swr_rev_stop"]))
        _t     = f["ca3_sup"]["spk_times"][:]
        _s     = f["ca3_sup"]["spk_senders"][:]
        _G     = f["ca3_sup"]["group_ids"][:]
        rho_f, p_f = score(_t, _s, _G, *fwd)
        rho_r, p_r = score(_t, _s, _G, *rev)
        g = f["stc"]
        tagged = g["n_tagged_syn"][:].astype(float)
        prp    = g["prp_mean"][:].astype(float)
        ltp    = g["n_ltp_total"][:].astype(float)
        wmean  = g["w_mean"][:].astype(float)
        wfinal = g["w_final"][:].astype(float)
        n_syn  = int(g.attrs["n_synapses"])
        w_init = float(g.attrs["w_init"])

    ev = np.arange(1, len(tagged) + 1)

    fig = plt.figure(figsize=(13.5, 8.6))
    gs  = GridSpec(2, 3, figure=fig, hspace=0.42, wspace=0.42)

    # ---- A / B  bidirectional replay ------------------------------------
    axA = fig.add_subplot(gs[0, 0])
    heat_panel(axA, H, times, fwd, "A  Forward replay (SWR-1)", C_FWD)
    axB = fig.add_subplot(gs[0, 1])
    im = heat_panel(axB, H, times, rev, "B  Reverse replay (SWR-2)", C_REV)
    cb = fig.colorbar(im, ax=axB, pad=0.02); cb.set_label("rate (Hz)", fontsize=8)

    # ---- C  replay quality ----------------------------------------------
    axC = fig.add_subplot(gs[0, 2])
    bars = axC.bar(["forward", "reverse"], [rho_f, rho_r],
                   color=[C_FWD, C_REV], width=0.55)
    axC.axhline(0, color="k", lw=0.8)
    for y, ls in ((0.5, "--"), (-0.5, "--")):
        axC.axhline(y, color="grey", ls=ls, lw=0.9)
    axC.text(1.52, 0.5, "PASS", fontsize=7, color="grey", va="bottom", ha="right")
    axC.text(1.52, -0.5, "PASS", fontsize=7, color="grey", va="top", ha="right")
    for b, v, p in zip(bars, (rho_f, rho_r), (p_f, p_r)):
        off = 0.06 if v > 0 else -0.06
        axC.text(b.get_x() + b.get_width() / 2, v + off, f"{v:+.3f}\np={p:.3f}",
                 ha="center", va="bottom" if v > 0 else "top", fontsize=8.5)
    axC.set_ylim(-1.15, 1.15)
    axC.set_ylabel(r"Spearman $\rho$  (group order vs time)")
    axC.set_title("C  Bidirectional replay quality", fontsize=10, loc="left",
                  fontweight="bold")
    axC.grid(axis="y", alpha=0.25)

    # ---- D  synaptic tagging --------------------------------------------
    axD = fig.add_subplot(gs[1, 0])
    axD.bar(ev, tagged / 1e3, color=C_TAG, alpha=0.85, label="tagged synapses")
    axD.set_xlabel("SWR event")
    axD.set_ylabel("tagged synapses (×10³)", color=C_TAG, fontsize=9)
    axD.tick_params(axis="y", labelcolor=C_TAG, labelsize=8)
    axD.set_title("D  Synaptic tagging", fontsize=10, loc="left", fontweight="bold")
    axDb = axD.twinx()
    axDb.plot(ev, prp, "-o", color="k", ms=3, lw=1.4)
    axDb.set_ylabel("PRP pool (SWR activations)", fontsize=9, labelpad=2)
    axDb.tick_params(labelsize=8)
    axD.grid(alpha=0.2)

    # ---- E  consolidation -------------------------------------------------
    axE = fig.add_subplot(gs[1, 1])
    axE.plot(ev, 100.0 * ltp / max(n_syn, 1), "-o", color=C_LTP, ms=3.5, lw=2,
             label="L-LTP synapses")
    axE.set_xlabel("SWR event")
    axE.set_ylabel("synapses with L-LTP (%)", color=C_LTP, fontsize=9)
    axE.tick_params(axis="y", labelcolor=C_LTP, labelsize=8)
    axE.set_title("E  Memory consolidation", fontsize=10, loc="left",
                  fontweight="bold")
    axEb = axE.twinx()
    axEb.plot(ev, wmean, "-s", color=C_W, ms=3, lw=1.5)
    axEb.set_ylabel("mean CA1→EC weight", color=C_W, fontsize=9, labelpad=2)
    axEb.tick_params(axis="y", labelcolor=C_W, labelsize=8)
    onset = np.argmax(ltp > 0) + 1 if (ltp > 0).any() else None
    if onset:
        axE.axvline(onset, color="grey", ls=":", lw=1.1)
        axE.annotate(f"L-LTP onset\nevent {onset}", xy=(onset, 5),
                     xytext=(onset + 1.5, 25), fontsize=8, color="dimgrey",
                     arrowprops=dict(arrowstyle="->", color="dimgrey", lw=0.8))
    axE.grid(alpha=0.2)

    # ---- F  engram --------------------------------------------------------
    axF = fig.add_subplot(gs[1, 2])
    axF.hist(wfinal, bins=60, color=C_W, alpha=0.85)
    axF.axvline(w_init, color="k", ls="--", lw=1.0)
    axF.text(w_init, axF.get_ylim()[1] * 0.92, " baseline", fontsize=8, color="k")
    axF.set_yscale("log")
    axF.set_xlabel("synaptic weight"); axF.set_ylabel("count (log)", fontsize=9)
    axF.tick_params(labelsize=8)
    axF.set_title("F  Consolidated CA1→EC weights", fontsize=10, loc="left",
                  fontweight="bold")
    pot = 100.0 * (wfinal > w_init * 1.05).mean()
    axF.text(0.97, 0.86, f"{pot:.0f}% potentiated", transform=axF.transAxes,
             ha="right", fontsize=9, color=C_W, fontweight="bold")
    axF.grid(alpha=0.2)

    fig.suptitle(f"tinyHippo — bidirectional replay, synaptic tagging and memory "
                 f"consolidation   [{scale}, {len(ev)} SWR events]",
                 fontsize=12.5, fontweight="bold", y=0.985)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f">>> Saved {args.out}")


if __name__ == "__main__":
    main()
