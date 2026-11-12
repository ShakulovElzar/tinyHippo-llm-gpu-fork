#!/usr/bin/env python3
"""Export the neuron-to-neuron wiring of a finished replay_scaled.py run.

The run's HDF5 file holds every spike but not the connections. NEST builds
the wiring once, from --seed, before the first nest.Simulate(). So this script
rebuilds the network with the SAME flags and thread count (same code, via
reconstruct_connectivity.build_network), stops before the simulation, and
saves every neuron->neuron synapse with its initial weight and delay.

    python viewer/export_wiring.py out/run1_1pct.h5

The flags come from <run>.flags.json (written by viewer/app.py), or pass them
after "--":  python viewer/export_wiring.py out/x.h5 -- --scale 1 --dg ...
Output: <run>_wiring.h5. Weights are the values at build time; plasticity
(STC, mPFC hooks) and the lesion change some of them later in the run.
"""

from __future__ import annotations

import json
import os
import sys
import time

import h5py
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import reconstruct_connectivity as rc  # noqa: E402

# HDF5 group -> key in replay_scaled's `net` dict, used to check that the
# rebuilt network has the same node IDs as the original run.
CHUNK = 1_000_000  # connections read per slice

NET_KEYS = {"ca3_sup": "CA3_SUP", "ca3_deep": "CA3_DEEP", "ca1_pyr": "PYR",
            "ca1_basket": "BASKET", "ca1_olm": "OLM"}


def main():
    argv = sys.argv[1:]
    if not argv:
        sys.exit(__doc__)
    run_h5 = os.path.abspath(argv[0])
    if "--" in argv:
        flags = argv[argv.index("--") + 1:]
    else:
        with open(run_h5[:-3] + ".flags.json") as f:
            flags = json.load(f)["flags"]
    flags = [a for a in flags if a != "--no-figures"] + ["--no-figures"]

    # Populations and their node-ID ranges, as recorded by the run itself.
    pops = []
    with h5py.File(run_h5, "r") as h5:
        for name in h5:
            g = h5[name]
            if isinstance(g, h5py.Group) and "gid_first" in g.attrs and "n_cells" in g.attrs:
                pops.append((name, int(g.attrs["gid_first"]), int(g.attrs["n_cells"])))
    pops.sort(key=lambda p: p[1])
    print(f">>> {len(pops)} populations in {os.path.basename(run_h5)}")

    os.chdir(REPO)
    rc.REPLAY_SCALED_PATH = os.path.join(REPO, "replay_scaled.py")
    rc.CAPTURE_FROM = []
    t0 = time.perf_counter()
    _, ns = rc.build_network(flags)
    import nest

    net = ns.get("net") or {}
    for name, gid_first, _ in pops:
        key = NET_KEYS.get(name)
        if key in net and int(net[key].tolist()[0]) != gid_first:
            sys.exit(f"!!! node IDs differ for {name}: the rebuild does not match the run. "
                     "Use the exact flags and --threads of the original run.")

    # One kernel scan (each GetConnections call scans every synapse, ~20 s at
    # 20M), then read fields in slices: reading all fields at once builds
    # Python lists for every synapse and can run out of memory.
    print(">>> reading connections from the NEST kernel ...")
    conns = nest.GetConnections()
    N = len(conns)
    print(f"    {N:,} connections found ({time.perf_counter()-t0:.0f}s)")
    fields = (("source", np.int64), ("target", np.int64), ("weight", np.float32), ("delay", np.float32))
    arrs = {k: np.empty(N, dtype=dt) for k, dt in fields}
    for a in range(0, N, CHUNK):
        sub = conns[a:min(N, a + CHUNK)]
        for k, _ in fields:
            v = sub.get(k)
            arrs[k][a:a + len(sub)] = v if isinstance(v, (list, tuple)) else [v]
        print(f"    {min(N, a + CHUNK):,}/{N:,} read ({time.perf_counter()-t0:.0f}s)")
    del conns
    src, tgt, w, dl = arrs["source"], arrs["target"], arrs["weight"], arrs["delay"]

    # Map node ID -> (population index, cell index); devices map to -1.
    starts = np.array([p[1] for p in pops])
    sizes = np.array([p[2] for p in pops])

    def locate(gid):
        k = np.searchsorted(starts, gid, side="right") - 1
        ok = (k >= 0) & (gid < starts[np.clip(k, 0, None)] + sizes[np.clip(k, 0, None)])
        k = np.where(ok, k, -1)
        return k, np.where(ok, gid - starts[np.clip(k, 0, None)], -1)

    sp, si = locate(src)
    tp, ti = locate(tgt)
    keep = (sp >= 0) & (tp >= 0)
    print(f">>> {keep.sum():,} neuron->neuron synapses kept (devices dropped)")

    out = run_h5[:-3] + "_wiring.h5"
    c = dict(compression="gzip", compression_opts=4)
    with h5py.File(out, "w") as h5:
        h5.attrs["source_run"] = os.path.basename(run_h5)
        h5.attrs["flags"] = json.dumps(flags)
        h5.attrs["note"] = "weights and delays at build time (before plasticity and lesion)"
        h5.create_dataset("pop_names", data=np.array([p[0] for p in pops], dtype="S"))
        h5.create_dataset("pop_gid_first", data=starts)
        h5.create_dataset("pop_n", data=sizes)
        h5.create_dataset("src_pop", data=sp[keep].astype(np.int16), **c)
        h5.create_dataset("src_idx", data=si[keep].astype(np.int32), **c)
        h5.create_dataset("tgt_pop", data=tp[keep].astype(np.int16), **c)
        h5.create_dataset("tgt_idx", data=ti[keep].astype(np.int32), **c)
        h5.create_dataset("weight", data=w[keep], **c)
        h5.create_dataset("delay", data=dl[keep], **c)
    print(f">>> wrote {out}")


if __name__ == "__main__":
    main()
