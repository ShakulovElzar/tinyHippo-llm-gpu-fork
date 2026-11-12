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
- ~~Only one config tested.~~ Closed in section 4.
- Merge risk: the diff touches 298 lines in `replay_scaled.py`/`tiny.py`, so any upstream change
  near a `nest.` call will conflict (decision D0, not asked to Max).

### 4. S0 extra configs: A, B, C

Purpose: test the shim on code paths that the reference config does not run.
Each config = reference flags (section 2) + the extra flags below, 1 thread, seed 202.
"Before" runs used a temporary checkout of `main` (`git worktree`, removed after). "After" runs used `shim`.
All 6 runs ran at the same time, 1 core each.

| config | extra flags | new code it runs | wall time | digest (main = shim) | result |
|---|---|---|---|---|---|
| A | `--homeostasis --schaffer-stdp` | weight downscaling after sleep; CA3→CA1 STDP | 28 min | `010e3cc8…aab5` | PASS |
| B | `--dg-neurogenesis --dg-perforant-stdp` | new DG cells created mid-run (+120 per epoch); EC→DG learning | 22 min | `615e8c72…bc4` | PASS |
| C | `--pattern-completion` | CA3 probe (runs instead of replay), intact vs ablated | 35 s | `05cc4b75…4edd` | PASS |

Result: **the shim is bit-identical on all 4 configs tested** (reference + A, B, C).

Notes:
- Config A: `[SchafferSTDP]` spent 1414 s reading 3,247,605 CA1-incoming synapses with
  `GetConnections`. That is most of the 28 min. This is the CPU cost that decision D1 compares
  against the GPU (Phase 0, connection get/set benchmark). Measured with 6 runs in parallel.
  Section 5 shows that 6 parallel runs are about 10× slower than one run alone, so this
  number is too high. Measure it again alone before using it.
- Config C: auto-association confirmed for 0/5 cue levels, on both `main` and `shim`. This is a
  model result at 1%, not a shim effect. Not checked further.
- First attempt of A and B failed at once (argparse exit 2): zsh passed the flags as one word.
  Re-run with separate words. Not a code problem.

### 5. Generator replacement: `--rhythm-gen spike_generator` (branch `shim`, not committed)

Problem: theta and ripple drive use NEST's `sinusoidal_poisson_generator`. NEST GPU does not have
it. Without a fix, `tiny.py` would catch the error and run **without theta** and with a **flat
ripple**: a silent model change on the GPU.

Fix (code):
- `tiny.py`: new `set_rhythm_generator(mode, horizon_ms, seed)`. In mode `spike_generator`,
  `sinusoidal_poisson_blocks()` computes the same random process in numpy (one Poisson count per
  0.1 ms step, rate = mean + amp·sin(2πft + phase), clipped at 0). `spike_generator` (which NEST
  GPU has) plays the trains back. The default path is unchanged.
- `replay_scaled.py`: new flags `--rhythm-gen {sinusoidal_poisson,spike_generator}` (default
  `sinusoidal_poisson`) and `--rhythm-horizon-ms`. Theta has no stop time, so trains are
  pre-computed to a horizon. Default horizon = sleep epochs + homeostasis epochs + cortical recall
  and G2 time + 1000 ms (9000 ms for the reference flags). A check before the HDF5 export warns if
  the run went past the horizon. New-mode HDF5 files get attrs `rhythm_gen`, `rhythm_horizon_ms`,
  `rhythm_n_spikes`. The random numbers come from their own generator (seed + 7301), so the
  model's other random streams do not change.

Check 1: device match (400 parrot neurons, NEST 3.10):

| drive | NEST device | spike_generator mode | waveform corr | noise floor (NEST vs NEST, other seed) |
|---|---|---|---|---|
| theta 1100±1000 Hz, 8 Hz | 1099.2 Hz | 1100.3 Hz | 0.999 | — |
| ripple 1100±850 Hz, 180 Hz, 300–420 ms | 1110.3 Hz | 1116.3 Hz | 0.992 | 0.992 |

- First version was 1 step (0.1 ms) late. NEST puts spikes at `start <= t < stop`. Fixed to match.

Check 2: default mode is unchanged. Old-device seed 202 = reference digest `2b17274a…399e`. PASS.

Check 3: full model, 3 seeds × 2 modes, reference flags, 1 thread.
Replay ρ per ripple (F = forward, R = reverse, block 1–4), DG % active in the 2 block-1 ripples,
mean rate.

| mode | seed | F1 | R1 | F2 | R2 | F3 | R3 | F4 | R4 | DG % f/r | CA3 SUP Hz | CA1 PYR Hz |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 202 | +0.84 | −0.41 | −0.04 | −0.06 | +0.01 | −0.55 | +0.53 | −0.43 | 3.57/3.33 | 20.6 | 9.9 |
| old | 303 | +0.72 | −0.60 | +0.20 | −0.53 | +0.25 | −0.03 | +0.54 | −0.24 | 3.53/2.88 | 19.7 | 9.1 |
| old | 404 | +0.54 | −0.42 | +0.09 | −0.18 | +0.39 | +0.03 | +0.49 | −0.15 | 2.83/2.57 | 20.1 | 9.2 |
| new | 202 | +0.55 | −0.74 | −0.09 | −0.22 | −0.10 | −0.31 | +0.65 | −0.98 | 3.48/**7.67** | 20.3 | 10.3 |
| new | 303 | +0.34 | −0.69 | +0.31 | −0.33 | +0.32 | +0.08 | +0.84 | −0.27 | **9.62**/2.94 | 19.9 | 9.6 |
| new | 404 | +0.81 | −0.49 | +0.09 | +0.31 | −0.38 | −0.41 | +0.50 | −0.77 | 3.16/2.46 | 20.2 | 9.7 |

Means: block-1 forward old +0.70, new +0.57. Block-1 reverse old −0.47, new −0.64.

Findings:
- Rates match (CA3 SUP about 20 Hz, CA1 PYR about 9.5 Hz in both modes).
- Replay: the new values are inside the seed-to-seed spread of the old values (block-1 forward
  +0.34 to +0.84). 3 seeds cannot show a small difference, so this is "no sign of a change",
  not "proven equal".
- DG: 2 of 6 new values are above the 2–4% band (7.67%, 9.62%). All 6 old values are in band.
  A sign that DG is very sensitive to the drive, not a fixed shift: the first new seed-202 run
  (horizon 7000 ms, so different theta random numbers) gave 3.48/3.96%. CLAUDE.md says DG is
  chaotic across blocks. **Open: run more seeds before calling this equal.**
- G2 and cortical recall fail in both modes (as before at 1%).

Problems found and fixed:
- First default horizon (epochs + 3000 ms) was too short. Seed 202 ran the G2 probe to 7800 ms;
  theta stopped at 7000 ms. The check printed the warning. Fixed the formula; re-ran seed 202.
- A different horizon changes the shape of the random draws, so the theta trains change too.
  Runs are repeatable only at the same seed **and** the same horizon.

Cost:
- Pre-computed theta spikes per 1% run: 67M (horizon 7000 ms) to 85M (9000 ms).
- One run alone: 201 s in new mode vs 131 s in old mode (+70 s for numpy and the spike_generators).
- At 12% (×12 neurons) this is about 1 billion spikes. Pre-computing everything is likely too big
  for the GPU. Better there: fill the trains one epoch at a time. This needs `SetStatus` of
  `spike_times` after `Simulate`, which Phase 0 must test on NEST GPU.
- 6 runs in parallel took 25–30 min each, about 10× slower than one run alone. Run fewer at a time.
