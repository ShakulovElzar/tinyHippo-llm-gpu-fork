# §51 scorer for the EC LV -> mPFC covariance rule. Usage: score_mpfc.py L.h5 N.h5 (same seed;
# L has mpfc_assoc with pre_gid/post_gid/w_init_arr).
# 1. synaptic: EC LV cells labelled by their preferred pattern (mean count per block, all blocks of L).
#    Per mPFC cell, mean dw of its EC LV inputs per label; stat = mean over cells of the variance
#    across labels; null = EC LV labels shuffled (1000).
# 2. functional: mPFC cells labelled by max-dw pattern (from L); group z with those labels,
#    second half, in L and in N.  3. LOO decoder on mPFC, L and N.
import sys, h5py, numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import decode_identity as D
L, N = h5py.File(sys.argv[1], 'r'), h5py.File(sys.argv[2], 'r'); rng = np.random.default_rng(0)
nb = int(L.attrs['n_epochs']); P = int(L.attrs['n_patterns']); ep = float(L.attrs['epoch_ms']); h = nb // 2
y = D.schedule(L, nb, P)
def counts(f, key):
    g = f[key]; n = int(g.attrs['n_cells'])
    X, _ = D.binned(g['spk_times'][:], g['spk_senders'][:], int(g.attrs['gid_first']), n, nb, ep)
    return X.sum(2), int(g.attrs['gid_first']), n
clv, glv, nlv = counts(L, 'ec_lv')
pref = np.stack([clv[y == k].mean(0) for k in range(P)], 1).argmax(1)
a = L['mpfc_assoc']; dw = a['w_final'][:] - a['w_init_arr'][:]
_, gpf, npf = counts(L, 'mpfc')
pre = a['pre_gid'][:] - glv; post = a['post_gid'][:] - gpf
def spec(lab):
    pp = lab[pre]; S = np.zeros((npf, P)); C = np.zeros((npf, P))
    np.add.at(S, (post, pp), dw); np.add.at(C, (post, pp), 1)
    M = np.where(C > 0, S / np.maximum(C, 1), np.nan); return np.nanvar(M, 1).mean(), M
obs, M = spec(pref)
null = np.array([spec(rng.permutation(pref))[0] for _ in range(1000)])
print(f'== {sys.argv[1]} vs {sys.argv[2]}  ({nb} blocks)')
print(f'  mpfc_assoc: mean dw/w0 {np.mean(dw / a["w_init_arr"][:]):+.4f}  spec {obs:.3e} null {null.mean():.3e} '
      f'z {(obs - null.mean()) / null.std():+.1f} p {(np.sum(null >= obs) + 1) / 1001:.4f}')
lab = np.nanargmax(np.nan_to_num(M, nan=-np.inf), 1)
for nm, f in (('L', L), ('N', N)):
    c, _, _ = counts(f, 'mpfc'); out = []
    for lo in (h, 0):
        cc = c[lo:]; Mm = np.stack([cc[:, lab == k].mean(1) for k in range(P)], 1)
        z = (Mm - Mm.mean(1, keepdims=True)) / (Mm.std(1, keepdims=True) + 1e-12)
        out.append(np.mean([z[i, y[lo:][i]] for i in range(len(z))]))
    print(f'  {nm}: mPFC dw-label z 2nd half {out[0]:+.3f}  all {out[1]:+.3f} | LOO mpfc {D.loo_acc(c, y, P):.2f}')
