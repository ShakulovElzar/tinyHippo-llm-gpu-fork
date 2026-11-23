# §45 consolidation scorer. Usage: score_cons.py L.h5 N.h5 (same seed; L has stc_lv).
# 1. synaptic: per EC LV cell, mean dw of its CA1 inputs per CA1 pattern (home group mod P);
#    stat = mean over cells of the variance across patterns; null = CA1 pattern labels shuffled.
# 2. functional: EC LV cells labelled by max-dw pattern (from L); group z with those labels,
#    second half, in L and in N.  3. LOO decoder (EC LV, mPFC), L and N.
import sys,h5py,numpy as np
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import decode_identity as D
L,N=h5py.File(sys.argv[1],'r'),h5py.File(sys.argv[2],'r'); rng=np.random.default_rng(0)
nb=int(L.attrs['n_epochs']); P=int(L.attrs['n_patterns']); ep=float(L.attrs['epoch_ms']); h=nb//2
G=L['ca3_sup/group_ids'][:].shape[0]
c1=L['ca1_pyr']; n1=int(c1.attrs['n_cells']); g1=int(c1.attrs['gid_first'])
hg1=c1['home_group'][:] if 'home_group' in c1 else np.arange(n1)%G
lv=L['ec_lv']; nlv=int(lv.attrs['n_cells']); glv=int(lv.attrs['gid_first'])
s=L['stc_lv']; dw=s['w_final'][:]-s['w_init'][:]; pre=s['pre_gid'][:]-g1; post=s['post_gid'][:]-glv
def spec(pat_of_ca1):
    pp=pat_of_ca1[pre]; S=np.zeros((nlv,P)); C=np.zeros((nlv,P))
    np.add.at(S,(post,pp),dw); np.add.at(C,(post,pp),1)
    M=np.where(C>0,S/np.maximum(C,1),np.nan); return np.nanvar(M,1).mean(),M
pat1=hg1%P; obs,M=spec(pat1)
null=np.array([spec(rng.permutation(pat1))[0] for _ in range(1000)])
print(f'== {sys.argv[1]} vs {sys.argv[2]}  ({nb} blocks)')
print(f'  stc_lv: mean dw {dw.mean():+.4f}  LTP {s["ltp_mask"][:].mean():.3f}  spec {obs:.3e} null {null.mean():.3e} z {(obs-null.mean())/null.std():+.1f} p {(np.sum(null>=obs)+1)/1001:.4f}')
lab=np.nanargmax(np.nan_to_num(M,nan=-np.inf),1)
y=D.schedule(L,nb,P)
def gz(f,key,labels,lo):
    g=f[key]; n=int(g.attrs['n_cells'])
    X,_=D.binned(g['spk_times'][:],g['spk_senders'][:],int(g.attrs['gid_first']),n,nb,ep); c=X.sum(2)[lo:]
    Mm=np.stack([c[:,labels==k].mean(1) for k in range(P)],1)
    z=(Mm-Mm.mean(1,keepdims=True))/(Mm.std(1,keepdims=True)+1e-12)
    return np.mean([z[i,y[lo:][i]] for i in range(len(z))]), c
for nm,f in (('L',L),('N',N)):
    a,_=gz(f,'ec_lv',lab,h); b,_=gz(f,'ec_lv',lab,0)
    accs=[]
    for key in ('ec_lv','mpfc'):
        g=f[key]; X,_=D.binned(g['spk_times'][:],g['spk_senders'][:],int(g.attrs['gid_first']),int(g.attrs['n_cells']),nb,ep)
        accs.append(D.loo_acc(X.sum(2),y,P))
    print(f'  {nm}: EC LV dw-label z 2nd half {a:+.3f}  all {b:+.3f} | LOO ec_lv {accs[0]:.2f} mpfc {accs[1]:.2f}')
