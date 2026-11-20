#!/usr/bin/env python3
"""Decode the cued memory from post-lesion mPFC spikes (WORKLOG section 19).

Needs runs made with --cortical-recall --g2-fixed-cue (g2_recall/cue_sets).

Train on sleep, test after the lesion. A decoder trained and tested on the
post-lesion trials alone is NOT valid: a fixed cue drives the same random
targets every trial, so it decodes the cue even without learning (WORKLOG 19).

Features: spike count of each mPFC cell, with EVERY cue cell of EVERY pattern
removed; each vector scaled to unit length (sleep and post-lesion activity
differ in size).
  train = one sample per consolidation epoch, counts in its two SWR windows,
          label = the pattern that epoch replayed;
  test  = one sample per post-lesion cue trial, counts in [t_cue, t_cue + WIN],
          label = the cued pattern.
Fixed wiring cannot make a cue of p drive the cells p drove during sleep; only
learning (or group wiring) can.

1. Decoder: L2 logistic regression (C=1, no intercept) fit on sleep, applied
   to the trials. A trial with no non-cue spike gets no prediction and scores
   1/k (chance). acc = mean over all trials. Null: shuffle the sleep-epoch
   labels and refit (n_perm); trial labels are not exchangeable, because a
   fixed cue fires the same cells on every trial. p = (#null >= real + 1) /
   (n_perm + 1).
2. MI (bits) between true and predicted label over responsive trials, plug-in
   estimate, minus the mean of the label-shuffle null.
3. Recurrent own-other weight change (mV): mean final mPFC->mPFC weight between
   cells of the same assembly minus between cells of different assemblies.

    python analysis/decode_postlesion.py out/idp/*.h5 [--perm 1000] [--json out.json]
"""
import argparse
import json

import h5py
import numpy as np
from sklearn.linear_model import LogisticRegression

WIN = 80.0  # ms, same window as the G2 response


def counts(t, s, n, wins):
    X = np.zeros((len(wins), n))
    for k, ws in enumerate(wins):
        for a, b in ws:
            sel = (t >= a) & (t <= b)
            np.add.at(X[k], s[sel], 1)
    return X


def unit(X):
    nrm = np.linalg.norm(X, axis=1, keepdims=True)
    return np.divide(X, nrm, out=np.zeros_like(X), where=nrm > 0)


def features(f):
    """(X_sleep, y_sleep, X_trial, y_trial, kept cell indices)."""
    g = f["g2_recall"]
    if "cue_sets" not in g:
        raise SystemExit("run lacks g2_recall/cue_sets: rerun with --g2-fixed-cue")
    m = f["mpfc"]
    g0, n = int(m.attrs["gid_first"]), int(m.attrs["n_cells"])
    t, s = m["spk_times"][:], m["spk_senders"][:].astype(np.int64) - g0
    a = f.attrs
    E, ep = float(a["epoch_ms"]), a["epoch_pattern"][:].astype(int)
    sleep = [[(e * E + a["swr_fwd_start"], e * E + a["swr_fwd_stop"]),
              (e * E + a["swr_rev_start"], e * E + a["swr_rev_stop"])]
             for e in range(len(ep))]
    t_cues, y = g["t_cues"][:], g["order"][:].astype(int)
    trials = [[(tc, tc + WIN)] for tc in t_cues]
    keep = np.setdiff1d(np.arange(n), np.unique(g["cue_sets"][:].ravel()) - g0)
    Xs, Xt = counts(t, s, n, sleep)[:, keep], counts(t, s, n, trials)[:, keep]
    return Xs, ep, Xt, y, keep


def predict(Xs, ys, Xt):
    """Fit on sleep, predict trials; -1 for a trial with no non-cue spike."""
    clf = LogisticRegression(C=1.0, fit_intercept=False, max_iter=5000)
    clf.fit(unit(Xs), ys)
    p = clf.predict(unit(Xt))
    p[Xt.sum(1) == 0] = -1
    return p


def score(p, y, k):
    resp = p >= 0
    return float(((p == y).sum() + (~resp).sum() / k) / len(y))


def mi_bits(yt, yp, k):
    c = np.zeros((k, k))
    np.add.at(c, (yt, yp), 1)
    p = c / c.sum()
    px, py = p.sum(1, keepdims=True), p.sum(0, keepdims=True)
    nz = p > 0
    return float((p[nz] * np.log2(p[nz] / (px @ py)[nz])).sum())


def own_other_weight(f):
    if "mpfc_recurrent" not in f:
        return None
    r, g = f["mpfc_recurrent"], f["g2_recall"]
    g0 = int(f["mpfc"].attrs["gid_first"])
    lab = np.full(int(f["mpfc"].attrs["n_cells"]), -1)
    for q, A in enumerate(g["assemblies"][:]):
        lab[A - g0] = q
    pre, post, w = r["pre_idx"][:], r["post_idx"][:], r["w_final"][:]
    a, b = lab[pre], lab[post]
    both = (a >= 0) & (b >= 0)
    same, diff = both & (a == b), both & (a != b)
    if not same.any() or not diff.any():
        return None
    return float(w[same].mean() - w[diff].mean())


def analyse(path, n_perm, seed=0):
    with h5py.File(path, "r") as f:
        Xs, ys, Xt, y, keep = features(f)
        k = int(y.max()) + 1
        p = predict(Xs, ys, Xt)
        resp = p >= 0
        acc, mi = score(p, y, k), mi_bits(y[resp], p[resp], k) if resp.any() else 0.0
        rng = np.random.default_rng(seed)
        null_acc, null_mi = np.empty(n_perm), np.empty(n_perm)
        for i in range(n_perm):
            # shuffle the SLEEP labels and refit: trials of one cue are not
            # independent (a fixed cue fires the same cells every time), so a
            # trial-label shuffle gives a null that is far too narrow.
            pn = predict(Xs, rng.permutation(ys), Xt)
            null_acc[i] = score(pn, y, k)
            null_mi[i] = mi_bits(y[resp], pn[resp], k) if resp.any() else 0.0
        g = f["g2_recall"]
        return dict(
            run=path, n_trials=len(y), frac_responsive=float(resp.mean()),
            n_features=int((Xt.sum(0) > 0).sum()), n_cells_kept=len(keep),
            assembly_size=int(g.attrs["assembly_size"]), chance=1.0 / k,
            acc=acc, null_acc_mean=float(null_acc.mean()),
            null_acc_95=float(np.quantile(null_acc, 0.95)),
            p=float((np.sum(null_acc >= acc) + 1) / (n_perm + 1)),
            mi_bits=mi, mi_corr_bits=mi - float(null_mi.mean()),
            g2_spec=float(g.attrs["specificity_mean"]), g2_p=float(g.attrs["p"]),
            own_other_w=own_other_weight(f),
            baseline=g["baseline"][:].tolist(),
        )


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("h5", nargs="+")
    ap.add_argument("--perm", type=int, default=1000)
    ap.add_argument("--json")
    a = ap.parse_args()
    rows = [analyse(p, a.perm) for p in a.h5]
    hdr = f"{'run':<22}{'resp':>5}{'acc':>7}{'null95':>8}{'p':>8}{'MIc':>7}{'G2':>8}{'G2 p':>8}{'own-oth w':>10}"
    print(hdr)
    for r in rows:
        w = "n/a" if r["own_other_w"] is None else f"{r['own_other_w']:+.3f}"
        print(f"{r['run'].split('/')[-1]:<22}{r['frac_responsive']:>5.2f}{r['acc']:>7.3f}"
              f"{r['null_acc_95']:>8.3f}{r['p']:>8.4f}{r['mi_corr_bits']:>+7.3f}"
              f"{r['g2_spec']:>+8.3f}{r['g2_p']:>8.4f}{w:>10}")
    if a.json:
        json.dump(rows, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
