#!/usr/bin/env python3
"""Learned CA1 -> EC LII weights, read per memory (LLM step 3c, WORKLOG 21).

Needs a run with --stc and --ec-memories (stc/pre_gid is saved only then).

Each CA1 -> EC LII synapse gets two pattern labels:
  pre  = CA1 PYR cell i -> group i % G -> pattern group % n_patterns
         (the labels the grouped CA1 -> EC wiring uses);
  post = EC LII home_group % n_patterns.
dw = final weight - initial weight (STC learning only; the no-learning twin
has dw = 0 everywhere, so this readout is learning by construction).

Statistic: mean dw on own synapses (pre pattern == post pattern) minus mean dw
on other synapses, in mV, plus the L-LTP fraction on each. Null: permute the
EC LII home labels across EC cells (n_perm). This keeps each cell's total
learning and asks only if it lands on the cell's own memory.
p = (#null >= real + 1) / (n_perm + 1).

Positive control (--plant MV): add MV to every own synapse before the test, to show
the readout can see a trace of that size. --plant-random MV adds it to a random set
of the same size instead (negative control: must not pass).

    python analysis/ec_weight_readout.py out/em/hyL_s202.h5 out/em/hyL_s303.h5
"""
import argparse

import h5py
import numpy as np


def own_other(dw, pre_pat, post_lab, post_idx, n_pat):
    own = pre_pat == (post_lab[post_idx] % n_pat)
    return dw[own].mean() - dw[~own].mean(), own


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("h5", nargs="+")
    ap.add_argument("--n-perm", type=int, default=2000)
    ap.add_argument("--plant", type=float, default=0.0, metavar="MV")
    ap.add_argument("--plant-random", type=float, default=0.0, metavar="MV")
    a = ap.parse_args()
    rng = np.random.default_rng(0)
    for path in a.h5:
        with h5py.File(path) as f:
            st = f["stc"]
            dw = st["w_final"][:] - float(st.attrs["w_init"])
            ltp = st["ltp_mask"][:].astype(bool)
            post_idx = st["post_idx"][:]
            pre = st["pre_gid"][:] - int(f["ca1_pyr"].attrs["gid_first"])
            G = f["ca3_sup/group_ids"].shape[0]
            n_pat = int(f.attrs["n_patterns"])
            lab = f["ec_lii/home_group"][:]
        pre_pat = (pre % G) % n_pat
        own0 = pre_pat == (lab[post_idx] % n_pat)
        dw = dw + a.plant * own0
        if a.plant_random:
            dw = dw + a.plant_random * np.isin(np.arange(len(dw)),
                                               rng.choice(len(dw), own0.sum(), replace=False))
        real, own = own_other(dw, pre_pat, lab, post_idx, n_pat)
        null = np.array([own_other(dw, pre_pat, rng.permutation(lab), post_idx, n_pat)[0]
                         for _ in range(a.n_perm)])
        p = (np.sum(null >= real) + 1) / (a.n_perm + 1)
        print(f"{path}: own-other dw {real*1000:+.3f} uV  p={p:.4f}  "
              f"(null {null.mean()*1000:+.3f} +- {null.std()*1000:.3f} uV)  "
              f"mean dw {dw.mean():+.4f}  L-LTP own {ltp[own].mean():.3f} other {ltp[~own].mean():.3f}  "
              f"own syn {own.mean():.2f}")


if __name__ == "__main__":
    main()
