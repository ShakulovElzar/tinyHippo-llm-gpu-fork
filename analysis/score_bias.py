# §46 follow-up: does EC LV follow the pattern bias of its random CA1 input? Usage: score_bias.py L.h5 N.h5
# Wiring (pre/post/w_init) from L's stc_lv (same seed => same build as N). Activity from N (no plasticity).
# Label A (wiring only): per EC LV cell, argmax over patterns of summed input weight from CA1 cells of
#   that pattern (CA1 home group mod P). Label B (predicted drive): sum of w x CA1 mean count per pattern,
#   CA1 counts from blocks 0-11; EC LV scored on blocks 12-23 (cross-validated).
# Stat: EC LV group z with those labels; null = labels shuffled across EC LV cells (1000).
import sys,h5py,numpy as np
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import decode_identity as D
L,N=h5py.File(sys.argv[1],'r'),h5py.File(sys.argv[2],'r'); rng=np.random.default_rng(0)
nb=int(N.attrs['n_epochs']); P=int(N.attrs['n_patterns']); ep=float(N.attrs['epoch_ms']); h=nb//2
G=N['ca3_sup/group_ids'][:].shape[0]; y=D.schedule(N,nb,P)
def counts(f,key):
    g=f[key]; X,_=D.binned(g['spk_times'][:],g['spk_senders'][:],int(g.attrs['gid_first']),int(g.attrs['n_cells']),nb,ep); return X.sum(2).astype(float)
c1=N['ca1_pyr']; n1=int(c1.attrs['n_cells']); g1=int(c1.attrs['gid_first']); pat1=np.arange(n1)%G%P
nlv=int(N['ec_lv'].attrs['n_cells']); glv=int(N['ec_lv'].attrs['gid_first'])
s=L['stc_lv']; pre=s['pre_gid'][:]-g1; post=s['post_gid'][:]-glv; w=s['w_init'][:]
K=np.bincount(post,minlength=nlv)
A=np.zeros((nlv,P)); np.add.at(A,(post,pat1[pre]),w)
C1=counts(N,'ca1_pyr'); R=np.stack([C1[:h][y[:h]==k].mean(0) for k in range(P)],1)   # CA1 cell x pattern
B=np.zeros((nlv,P)); np.add.at(B,post,w[:,None]*R[pre])
clv=counts(N,'ec_lv')[h:]; yy=y[h:]
def gz(lab):
    M=np.stack([clv[:,lab==k].mean(1) if (lab==k).any() else np.zeros(len(yy)) for k in range(P)],1)
    z=(M-M.mean(1,keepdims=True))/(M.std(1,keepdims=True)+1e-12); return z[np.arange(len(yy)),yy].mean()
print(f'== {sys.argv[2]}: EC LV {nlv} cells, CA1 inputs per cell {K.mean():.0f}')
for nm,X in (('wiring',A),('drive',B)):
    lab=X.argmax(1); fr=np.sort(X/X.sum(1,keepdims=True),1)
    o=gz(lab); nu=np.array([gz(rng.permutation(lab)) for _ in range(1000)])
    print(f'  {nm}: top-pattern input share {fr[:,-1].mean():.3f} (1/P={1/P:.3f})  group z {o:+.3f}  null {nu.mean():+.3f}±{nu.std():.3f}  p {(np.sum(nu>=o)+1)/1001:.4f}')
