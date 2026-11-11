# Work log: tinyHippo-llm-gpu (local Mac)

Personal log, committed on branch `shim`. Machine: Apple M4, 10 cores, 17 GB RAM, macOS.
NEST 3.10.0 (Homebrew), Python 3.15.2, `.venv` with `--system-site-packages`.
Max's baseline (RESULTS_llm_gpu §1) used an Apple M3 with NEST 3.9.0.

---

## 2026-11-10: setup, tests, viewer, first runs

1. Cloned `max-talanov/tinyHippo-llm-gpu`. Made the fork `ShakulovElzar/tinyHippo-llm-gpu-fork`.
   Remotes: `origin` = my fork, `upstream` = Max's repo, `private` = my private copy.
2. Made `.venv`. Installed numpy, scipy, pytest, anthropic. Built h5py from source against
   `brew install hdf5`, because no h5py wheel exists for Python 3.15.
   I did not use `requirements.txt`: its `numpy<2.0` pin breaks Homebrew NEST.
3. Ran the L0 tests on branch `llm-l0`: 8/8 pass.
4. Built the viewer (`viewer/`, branch `viewer`, not committed):
   - `viewer/app.py`: local web server on http://127.0.0.1:8765. Reads run HDF5 files in `out/`.
     Starts new runs (form "New run").
   - `viewer/export_wiring.py`: rebuilds the network with the same flags and saves every
     neuron-to-neuron synapse to `out/<run>_wiring.h5`. The run HDF5 has spikes only, no wiring.
   - `viewer/index.html`: circuit map, Replay panel, spike raster, neuron inspector.
5. Runs (all 1%, full-loop config = Max's baseline flags, 4 sleep blocks):

   | run | seed | threads | note |
   |---|---|---|---|
   | `run1_1pct` | 202 | 8 | first run, 3 min 20 s |
   | `test_launcher` | 202 | 8 | short "replay + DG" preset test |

---

## 2026-11-11

### 1. Seed 303 run: `run4_seed303`

- Started through the viewer server:
  `POST /api/launch {"name":"run4_seed303","preset":"full-loop","scale":1,"threads":8,"seed":303,"n_swr":4}`.
- Checked `out/run4_seed303.flags.json`: seed = 303.
- Time: about 3 min simulation + 2 min wiring export. 6,004,969 synapses.

Replay score per ripple (Spearman ρ, CA3 SUP, inside the SWR window).
+1 = clean forward order, −1 = clean reverse order.

| run | seed | fwd1 | rev1 | fwd2 | rev2 | fwd3 | rev3 | fwd4 | rev4 |
|---|---|---|---|---|---|---|---|---|---|
| run1_1pct | 202 | +0.81 | −0.65 | +0.42 | +0.28 | −0.26 | −0.55 | +0.56 | −0.14 |
| run4_seed303 | 303 | +0.79 | −0.49 | +0.39 | +0.04 | −0.19 | +0.12 | +0.79 | −0.89 |

Findings:
- Block 1 forward replay is good on both seeds (about +0.8).
- Block 1 reverse is weaker on seed 303 (log: `rho=-0.491 p=0.150 [WEAK]`).
- Blocks 2–4 are not reliable. The simulation log prints only block 1, so the log hides this.
- Cortical recall after the lesion fails on both seeds: "no cortical recall above baseline",
  0 L-LTP synapses. Max's §1 says this is expected at 1% with 4 blocks.
- All of this is 1% and 2 seeds: a pilot, not a result (CLAUDE.md rule).

### 2. S0 reference runs (started 12:46 CET)

Purpose: make the "before" file for the S0 test, and check that 1-thread runs repeat exactly
on this machine (NEST 3.10, not Max's 3.9).

- Run A: `s0_ref_t1`. Run B: `s0_ref_t1_b`. Both started through the viewer server,
  one after the other (the server allows one run at a time).
- Flags (same as Max's baseline, but `--threads 1`):

  ```
  --scale 1 --threads 1 --seed 202 --n-swr 4 --ec-lii --ec-lii-k 50 --n-patterns 3
  --schaffer-k 500 --schaffer-group-frac 0.7 --ca1-ec-group-frac 0.7 --cortex-group-frac 0.7
  --cortical-recall --cr-cue-frac 0.4 --cr-prime-rate 120 --cr-prime-weight 1.0
  --dg --dg-scale 1 --het 0.30 --het-wcomp 2.3 --w-ec-dg 0.6 --pp-residual 0.9 --dg-delay-jitter 4.0
  --pattern-source ca3 --stc --epoch-ms 1000 --prp-threshold 14.0 --ec-lv --mpfc
  --no-figures --out-hdf5 out/s0_ref_t1.h5
  ```

  Flag order differs from Max's script; argparse does not care about order.
  `PYTHONHASHSEED` is not set. Max found that it has no effect.
- Comparison tool: Max's `h5_digest.py` from branch `llm-l0`, copied with
  `git show llm-l0:h5_digest.py` (no branch switch). It hashes all data and attributes except
  `created_utc`.
- Max's reference digest (M3, NEST 3.9): `1e218550c850e2a3…`. Our digest can differ, because
  NEST 3.10 is a different version. That is not a failure. The test is A = B on this machine.

Result: **PASS. Run A and run B are bit-identical.**

```
2b17274a9c512715c09aeb3466c483ecacba96df8f8d3a0d1a7b1c440b09399e  out/s0_ref_t1.h5
2b17274a9c512715c09aeb3466c483ecacba96df8f8d3a0d1a7b1c440b09399e  out/s0_ref_t1_b.h5
--diff: identical
```

- **S0 reference digest for this machine (NEST 3.10, 1 thread):**
  `2b17274a9c512715c09aeb3466c483ecacba96df8f8d3a0d1a7b1c440b09399e`.
  It differs from Max's 3.9 digest (`1e218550…`), as expected for a different NEST version.
- Replay in block 1 (both runs): forward ρ = +0.842 (p = 0.002, PASS), reverse ρ = −0.406
  (p = 0.244, WEAK). DG active: 3.57% / 3.33% (target 2–4%, PASS).
- Time: run A 12:46 → 12:49, run B 12:49 → 12:52, wiring export included.
  Simulation wall time 130.8 s with 1 thread. The 8-thread run `run4_seed303` took 179.7 s.
  So on this M4, 1 thread was faster than 8 threads. One measurement each; not checked further.

How to repeat the check after a code change (for S0):

```bash
.venv/bin/python replay_scaled.py <flags above> --out-hdf5 out/s0_after.h5
git show llm-l0:h5_digest.py > /tmp/h5_digest.py
.venv/bin/python /tmp/h5_digest.py out/s0_ref_t1.h5 out/s0_after.h5
```

Same digest = the change did not alter the model. Different = use `--diff` to see which data changed.

### 3. S0 shim: `simbackend.py` (branch `shim`)

Branch `shim` made from `main` (`4e84158`). Committed on `shim`, not pushed.

What changed:

| file | change |
|---|---|
| `simbackend.py` | new, 95 lines. The one place that imports NEST. |
| `tiny.py` | 85 `nest.X` calls → `sim.X`; `import nest` → `import simbackend as sim` |
| `replay_scaled.py` | 189 `nest.X` calls → `sim.X`; 22 local `import nest` and 1 `from nest import` re-routed; new flag `--backend {nest}` (default `nest`) |

Design decisions:
- The shim functions keep the PyNEST names (`sim.Create`, `sim.Connect`, `sim.GetStatus`, ...).
  New names like `create_izh` (migration plan, Phase 1) would mean rewriting each call by hand,
  which puts the random number order at risk. NEST GPU's Python API uses the same names.
- Each shim function looks up the NEST function at call time. `reconstruct_connectivity.py`
  (used by the viewer's wiring export) replaces `nest.Simulate` at runtime and needs this.
- `NodeCollection`, `SynapseCollection`, `random`, `math` are passed through unchanged,
  so `isinstance()` checks and NEST parameter expressions still work.
- Two hand edits: `nest.node_models` → `sim.node_models()`, and
  `_nest.__version__` → `sim.version()`.
- The re-route was done with a script that uses Python's `tokenize`. It changes only code
  tokens, so comments and docstrings that say `nest.Connect` stay as they are.
  (The earlier count of 216 for `replay_scaled.py` included about 26 of these.)

Tests (1 thread, reference flags from section 2):

| test | output | digest | result |
|---|---|---|---|
| after `tiny.py` only | `out/s0_after_tiny.h5` | `2b17274a…399e` | PASS |
| full shim, `--backend nest` | `out/s0_after_shim.h5` | `2b17274a…399e` | PASS |
| wiring export (viewer) | `out/s0_after_shim_wiring.h5` | all 9 datasets equal to `s0_ref_t1_wiring.h5` (6,004,663 synapses) | PASS |

Result: **S0 gate passes. The shim does not change the model.**

Not covered (open items):
- Methods on NEST objects (`pop.get(...)`, `conns.set(...)`, slicing) still go to NEST
  directly. That is up to 55 `.get(`/`.set(` lines (some are plain dict `.get`). S1 must
  check these for NEST GPU.
- Other scripts still import NEST directly: `reconstruct_connectivity.py`,
  `bidirectional_replay*.py`, `nest_dg_ca3_fi_calibration.py`, `check_nest.py`. S0 covers only
  `replay_scaled.py` and `tiny.py`, as the plan says.
- Only one config tested (the full-loop 1% reference). Flags that this config does not use
  (e.g. `--homeostasis`, `--pattern-completion`) run code paths that no test covered.
- Merge risk: the diff touches 298 lines in `replay_scaled.py`/`tiny.py`, so any upstream change
  near a `nest.` call will conflict (decision D0, not asked to Max).
