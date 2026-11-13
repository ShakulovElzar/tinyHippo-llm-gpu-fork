#!/usr/bin/env python3
"""
make_paper_figure.py
=====================
Generates the main triple-falsification figure for the tinyHippo paper.

Three columns, three conditions:
  Run A   : Normal STC (PRP_threshold = 3.5)              -> consolidation works
  Run B   : Synthesis-blocked (PRP_threshold = 999)       -> consolidation fails
  Phase 4 : CA3 recurrent downscaled by alpha = 0.75      -> engram persists

Three rows of evidence:
  Top    : L-LTP fraction over SWR events
  Middle : Replay quality (rho_fwd Spearman) bars
  Bottom : Final CA1->EC weight distribution
"""
import os
import h5py
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- dark theme (project house style) -----------------------------------
plt.style.use("dark_background")
plt.rcParams.update({
    "figure.facecolor":  "#0d1117",
    "axes.facecolor":    "#161b22",
    "savefig.facecolor": "#0d1117",
    "axes.edgecolor":    "#8b949e",
    "axes.labelcolor":   "#c9d1d9",
    "xtick.color":       "#c9d1d9",
    "ytick.color":       "#c9d1d9",
    "text.color":        "#c9d1d9",
    "axes.grid":         True,
    "grid.color":        "#30363d",
    "grid.alpha":        0.4,
    "grid.linewidth":    0.5,
    "font.size":         10,
})

# ---- file paths ---------------------------------------------------------
F_A   = "replay_25pct_stc_lv_mpfc.h5"        # Run A
F_B   = "replay_25pct_stc_lv_mpfc_ph5.h5"    # Run B
F_PH4 = "replay_25pct_stc_lv_mpfc_ph4.h5"    # Phase 4

# ---- pull data ----------------------------------------------------------
def load(path):
    with h5py.File(path, "r") as f:
        d = {
            "n_ltp_total": f["stc/n_ltp_total"][:],
            "w_mean":      f["stc/w_mean"][:],
            "w_final":     f["stc/w_final"][:],
            "rho_fwd":     float(f["stats"].attrs["rho_fwd"]),
            "pval_fwd":    float(f["stats"].attrs["pval_fwd"]),
        }
        if "homeostasis" in f:
            attrs = dict(f["homeostasis"].attrs)
            d["rho_fwd_post"] = float(attrs["rho_fwd_post_homeo"])
            d["alpha"]        = float(attrs["alpha"])
            d["ca3_pre"]      = float(attrs["ca3_w_pre_mean"])
            d["ca3_post"]     = float(attrs["ca3_w_post_mean"])
        return d

A   = load(F_A)
B   = load(F_B)
PH4 = load(F_PH4)

N_TOTAL = 1_275_000
def frac(arr):  return arr / N_TOTAL * 100.0

# ---- colour scheme ------------------------------------------------------
C_A   = "#58a6ff"   # blue   = normal consolidation
C_B   = "#f85149"   # red    = synthesis blocked (Phase 5 falsification)
C_PH4 = "#a371f7"   # purple = post-homeostasis

# ========================================================================
#  Build figure: 3 rows x 3 cols, but with a custom layout
# ========================================================================
fig = plt.figure(figsize=(15, 11))
gs  = fig.add_gridspec(3, 3, height_ratios=[1.0, 0.8, 1.0], hspace=0.45, wspace=0.32,
                       left=0.07, right=0.97, top=0.92, bottom=0.07)

fig.suptitle(
    "tinyHippo  -  triple falsification of the replay$\\to$consolidation circuit  [25% scale]",
    fontsize=14, fontweight="bold", y=0.975,
)

# ------------------------------------------------------------------------
# ROW 1: consolidation curves (L-LTP %)  -- single wide panel spanning all 3 cols
# ------------------------------------------------------------------------
ax_top = fig.add_subplot(gs[0, :])

ev_A   = np.arange(1, len(A["n_ltp_total"]) + 1)
ev_B   = np.arange(1, len(B["n_ltp_total"]) + 1)
ev_PH4 = np.arange(1, len(PH4["n_ltp_total"]) + 1)

ax_top.plot(ev_A,   frac(A["n_ltp_total"]),   "-o", color=C_A,   lw=3.0, ms=8,
            label="Run A: normal STC (PRP$_\\mathrm{th}$=3.5)", alpha=0.95)
ax_top.plot(ev_B,   frac(B["n_ltp_total"]),   "-s", color=C_B,   lw=2.5, ms=6,
            label="Run B: synthesis blocked (PRP$_\\mathrm{th}$=999)")
ax_top.plot(ev_PH4, frac(PH4["n_ltp_total"]), "--^", color=C_PH4, lw=1.6, ms=8,
            mfc="none", mec=C_PH4, mew=1.6,
            label=f"Phase 4: CA3 down-scaled $\\alpha$={PH4['alpha']:.2f}  (CA1$\\to$EC L-LTP intact)")

ax_top.axvline(4, ls="--", color="#f0883e", lw=1.2, alpha=0.7)
ax_top.text(4.2, 50, "First L-LTP @ event 4\n(Frey & Morris 1997)",
            color="#f0883e", fontsize=9, va="center")

ax_top.set_xlabel("SWR event #", fontsize=11)
ax_top.set_ylabel("L-LTP fraction (% of CA1$\\to$EC synapses)", fontsize=11)
ax_top.set_title("A   Consolidation timeline -- L-LTP captured per SWR event",
                 fontsize=11, loc="left", fontweight="bold")
ax_top.set_ylim(-3, 105)
ax_top.legend(loc="center right", fontsize=9, framealpha=0.85,
              facecolor="#161b22", edgecolor="#30363d")

# ------------------------------------------------------------------------
# ROW 2: rho_fwd bars (3 conditions)  +  CA3 weight summary annotations
# ------------------------------------------------------------------------
ax_rho = fig.add_subplot(gs[1, 0])
ax_w3  = fig.add_subplot(gs[1, 1])
ax_ll  = fig.add_subplot(gs[1, 2])

# --- rho bars ---
labels    = ["Run A\n(normal)", "Run B\n(PRP=999)", "Phase 4\n(post-homeo)"]
rho_vals  = [A["rho_fwd"], B["rho_fwd"], PH4["rho_fwd_post"]]
bar_cols  = [C_A, C_B, C_PH4]
bars = ax_rho.bar(labels, rho_vals, color=bar_cols, edgecolor="white", lw=0.8)
for bar, val in zip(bars, rho_vals):
    ax_rho.text(bar.get_x() + bar.get_width()/2, val + 0.03 if val > 0 else val - 0.06,
                f"{val:+.3f}", ha="center", fontsize=10, fontweight="bold")
ax_rho.axhline(0, color="white", lw=0.5)
ax_rho.axhline( 0.5, ls=":", color="#8b949e", lw=0.7)
ax_rho.axhline(-0.5, ls=":", color="#8b949e", lw=0.7)
ax_rho.set_ylim(-0.2, 1.0)
ax_rho.set_ylabel(r"$\rho_\mathrm{fwd}$  (Spearman)", fontsize=11)
ax_rho.set_title("B   Replay quality (CA3 SUP)",
                 fontsize=11, loc="left", fontweight="bold")
ax_rho.grid(axis="y")

# --- CA3 weight bars (homeostasis verification) ---
ca3_pre   = PH4["ca3_pre"]
ca3_post  = PH4["ca3_post"]
ax_w3.bar(["pre-homeo", "post-homeo"], [ca3_pre, ca3_post],
          color=["#8b949e", C_PH4], edgecolor="white", lw=0.8)
ax_w3.text(0, ca3_pre  + 0.015, f"{ca3_pre:.4f}",  ha="center", fontsize=10, fontweight="bold")
ax_w3.text(1, ca3_post + 0.015, f"{ca3_post:.4f}", ha="center", fontsize=10, fontweight="bold")
ratio = ca3_post / ca3_pre
ax_w3.text(0.5, 0.85, f"ratio = {ratio:.3f}\n(target $\\alpha$ = {PH4['alpha']:.2f})",
           transform=ax_w3.transAxes, ha="center", fontsize=9,
           bbox=dict(facecolor="#161b22", edgecolor=C_PH4, lw=0.8, pad=4))
ax_w3.set_ylabel("Mean CA3 recurrent EXC weight", fontsize=11)
ax_w3.set_title("C   Homeostasis verification\n     (2.61M synapses)",
                fontsize=11, loc="left", fontweight="bold")
ax_w3.set_ylim(0, ca3_pre * 1.15)
ax_w3.grid(axis="y")

# --- L-LTP final fraction bars ---
final_ll = [frac(A["n_ltp_total"])[-1],
            frac(B["n_ltp_total"])[-1],
            frac(PH4["n_ltp_total"])[-1]]
bars3 = ax_ll.bar(labels, final_ll, color=bar_cols, edgecolor="white", lw=0.8)
for bar, val in zip(bars3, final_ll):
    ax_ll.text(bar.get_x() + bar.get_width()/2, val + 1.5,
               f"{val:.1f}%", ha="center", fontsize=10, fontweight="bold")
ax_ll.set_ylabel("Final L-LTP %", fontsize=11)
ax_ll.set_ylim(0, 110)
ax_ll.set_title("D   Cortical engram (CA1$\\to$EC)",
                fontsize=11, loc="left", fontweight="bold")
ax_ll.grid(axis="y")

# ------------------------------------------------------------------------
# ROW 3: weight distribution histograms (3 conditions, side by side)
# ------------------------------------------------------------------------
ax_hA   = fig.add_subplot(gs[2, 0])
ax_hB   = fig.add_subplot(gs[2, 1])
ax_hPH4 = fig.add_subplot(gs[2, 2])

bins = np.linspace(0.85, 1.55, 71)

def plot_hist(ax, w, color, title, subtitle):
    ax.hist(w, bins=bins, color=color, edgecolor="white", lw=0.3, alpha=0.85)
    ax.axvline(1.0, ls=":", color="#8b949e", lw=1.0, label="$w_\\mathrm{init}$ = 1.0")
    ax.axvline(1.5, ls=":", color="#3fb950", lw=1.0, label="L-LTP plateau (1.5)")
    ax.set_yscale("log")
    ax.set_ylim(1, 5e6)
    ax.set_xlabel("Synaptic weight (CA1$\\to$EC)", fontsize=10)
    ax.set_ylabel("# synapses (log)", fontsize=10)
    ax.set_title(title, fontsize=10.5, loc="left", fontweight="bold")
    # Annotation in upper-LEFT, legend in upper-CENTER (below annotation)
    ax.text(0.03, 0.97, subtitle, transform=ax.transAxes,
            va="top", ha="left", fontsize=8.0,
            bbox=dict(facecolor="#0d1117", edgecolor="#30363d", lw=0.6, pad=4))
    ax.legend(fontsize=7.5, loc="lower center",
              facecolor="#161b22", edgecolor="#30363d", framealpha=0.9)

plot_hist(ax_hA,   A["w_final"],   C_A,
          "E   Run A: final weight dist.",
          f"mean = {A['w_final'].mean():.3f}\n"
          f"L-LTP = {frac(A['n_ltp_total'])[-1]:.1f}%\n"
          f"$\\to$ plateau at 1.5\n     (consolidated)")
plot_hist(ax_hB,   B["w_final"],   C_B,
          "F   Run B: final weight dist.",
          f"mean = {B['w_final'].mean():.3f}\n"
          f"L-LTP = {frac(B['n_ltp_total'])[-1]:.1f}%\n"
          f"$\\to$ E-LTP only,\n     no PRP capture")
plot_hist(ax_hPH4, PH4["w_final"], C_PH4,
          "G   Phase 4: final weight dist.",
          f"mean = {PH4['w_final'].mean():.3f}\n"
          f"L-LTP = {frac(PH4['n_ltp_total'])[-1]:.1f}%\n"
          f"$\\to$ engram intact\n     ($\\alpha$={PH4['alpha']:.2f} on CA3)")

# ---- save ---------------------------------------------------------------
out_dir = "out/"
os.makedirs(out_dir, exist_ok=True)

png_path = os.path.join(out_dir, "fig_triple_falsification.png")
pdf_path = os.path.join(out_dir, "fig_triple_falsification.pdf")

fig.savefig(png_path, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
fig.savefig(pdf_path,           bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close(fig)

print(f"Saved {png_path}")
print(f"Saved {pdf_path}")
