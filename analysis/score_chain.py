# Home-group z with 95% CI over blocks, p, halves and SWR-window Hz for CA3 SUP, CA1, EC LV, mPFC.
import sys,h5py,numpy as np
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import decode_identity as D
W=[(300,420),(600,720)]
for p in sys.argv[1:]:
    f=h5py.File(p,'r'); nb=int(f.attrs['n_epochs']); P=int(f.attrs['n_patterns']); ep=float(f.attrs['epoch_ms'])
    sch=D.schedule(f,nb,P); gids=f['ca3_sup/group_ids'][:]; G=gids.shape[0]; rng=np.random.default_rng(0)
    print(f'== {p} ({nb} blocks)')
    for key in ['ca3_sup','ca1_pyr','ec_lv','mpfc']:
        n=int(f[key].attrs['n_cells']); g0=int(f[key].attrs['gid_first']); t=f[key+'/spk_times'][:]
        X,_=D.binned(t,f[key+'/spk_senders'][:],g0,n,nb,ep); c=X.sum(2)
        if key=='ca3_sup': idx=[gids[g]-gids.min() for g in range(G)]
        else:
            hg=f[key+'/home_group'][:] if 'home_group' in f[key] else np.arange(n)%G
            idx=[np.flatnonzero(hg==g) for g in range(G)]
        M=np.stack([c[:,ix].mean(1) for ix in idx],1); z=D.group_z(M,sch,P)
        _,pv=D.perm_p(lambda sc: D.group_z(M,sc,P).mean(),sch,rng,2000)
        se=z.std(ddof=1)/np.sqrt(nb); h=nb//2
        hz=sum(((t>=b*ep+a)&(t<b*ep+e)).sum() for b in range(nb) for a,e in W)/n/(nb*0.24)
        print(f'  {key}: z {z.mean():+.3f} [{z.mean()-1.96*se:+.2f}, {z.mean()+1.96*se:+.2f}] p {pv:.4f}  halves {z[:h].mean():+.2f} / {z[h:].mean():+.2f}  {hz:.1f} Hz')
