"""Population activity profiles — what heterogeneity does to the network.

Rate traces per population, one column per configuration, SWR windows shaded.
The point of the figure is the SHAPE of activity, not just the mean rate: a
matched mean can hide a population that has stopped being SWR-locked.
"""
import glob
import os
import sys
import numpy as np, h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

POPS = [("CA3 SUP","ca3_sup"), ("CA1 PYR","ca1_pyr"), ("EC LII","ec_lii"),
        ("mPFC","mpfc"), ("CA1 basket","ca1_basket"), ("CA3 int","ca3_int_sup")]
BIN = 5.0

def rate_trace(f, pop, t_max):
    if pop not in f: return None, None
    t = f[pop]["spk_times"][:]
    n = int(f[pop].attrs.get("n_cells", 0)) or max(len(np.unique(f[pop]["spk_senders"][:])),1)
    edges = np.arange(0, t_max+BIN, BIN)
    c,_ = np.histogram(t, bins=edges)
    return edges[:-1], c/(n*BIN/1000.0)

def main(specs, out):
    fig, axes = plt.subplots(len(POPS), len(specs), figsize=(4.2*len(specs), 1.7*len(POPS)),
                             sharex=True, squeeze=False)
    for ci,(label,path) in enumerate(specs):
        f = h5py.File(path)
        fwd=(float(f.attrs["swr_fwd_start"]), float(f.attrs["swr_fwd_stop"]))
        rev=(float(f.attrs["swr_rev_start"]), float(f.attrs["swr_rev_stop"]))
        t_max = max(f[p]["spk_times"][:].max() for _,p in POPS if p in f)
        n_ep = int(np.ceil(t_max/1000.0))
        for ri,(nice,pop) in enumerate(POPS):
            ax = axes[ri][ci]
            x,y = rate_trace(f, pop, t_max)
            if x is None:
                ax.text(.5,.5,"absent",ha="center",va="center",transform=ax.transAxes,
                        color="0.6"); ax.set_yticks([])
            else:
                for e in range(n_ep):
                    ax.axvspan(e*1000+fwd[0], e*1000+fwd[1], color="#4C78A8", alpha=.13, lw=0)
                    ax.axvspan(e*1000+rev[0], e*1000+rev[1], color="#E45756", alpha=.13, lw=0)
                ax.plot(x, y, lw=.8, color="#333")
                ax.set_ylabel(f"{nice}\nHz", fontsize=8)
                ax.text(.99,.86,f"mean {y.mean():.2f} Hz", transform=ax.transAxes,
                        ha="right", va="top", fontsize=7, color="#B03A2E")
            ax.tick_params(labelsize=7)
            if ri==0: ax.set_title(label, fontsize=10, fontweight="bold")
            if ri==len(POPS)-1: ax.set_xlabel("time (ms)", fontsize=8)
        f.close()
    fig.suptitle("Population activity profiles — blue = forward SWR window, red = reverse",
                 fontsize=11, y=.995)
    fig.tight_layout(rect=[0,0,1,.985])
    fig.savefig(out, dpi=130)
    print("wrote", out)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        description="Compare population rate traces of several runs, one column per run.",
        epilog="example: python plots/plot_activity_profiles.py base=out/cx_s202.h5 "
               "lr03=out/ra03_s202.h5 --out out/activity.png")
    ap.add_argument("runs", nargs="+", metavar="LABEL=FILE.h5")
    ap.add_argument("--out", default="out/activity_profiles.png")
    a = ap.parse_args()
    specs = [r.split("=", 1) if "=" in r else (os.path.basename(r), r) for r in a.runs]
    main([(l, p) for l, p in specs if glob.glob(p)], a.out)
