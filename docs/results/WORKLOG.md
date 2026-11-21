# Work log: tinyHippo-llm-gpu (local Mac)

Personal log, on branch `llm-work` (first written on `shim`, which was merged and deleted in
section 15). Machine: Apple M4, 10 cores, 16 GB RAM, macOS.
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
4. Built the viewer (`viewer/`, branch `viewer`; committed later in `90d2bec`):
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
  (Studied in depth in sections 7 and 18.)
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

How to repeat the check after a code change (for S0). Updated: the script is now
`analysis/h5_digest.py`, and the valid reference is `8631eb29…` (`out/s0_fix.h5`, section 6),
not `2b17274a…`:

```bash
.venv/bin/python replay_scaled.py <flags above> --out-hdf5 out/s0_after.h5
.venv/bin/python analysis/h5_digest.py out/s0_fix.h5 out/s0_after.h5
```

Same digest = the change did not alter the model. Different = use `--diff` to see which data changed.

### 3. S0 shim: `simbackend.py` (branch `shim`)

Branch `shim` made from `main` (`4e84158`). Committed on `shim` (later merged; `shim` deleted in section 15).

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

### 5. Generator replacement: `--rhythm-gen spike_generator` (branch `shim`; committed later in `581393d`)

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

### 6. Code review fixes (branch `shim`)

A code review found 10 problems. All 10 are fixed. The model's spikes and wiring do not change.

| # | file | problem | fix |
|---|---|---|---|
| 1 | `replay_scaled.py` | MPI: EC LV / mPFC spikes were gathered after ranks > 0 returned, so rank 0 waited forever | gather them before the return |
| 2 | `replay_scaled.py`, `decode_identity.py` | the HDF5 had no pattern schedule; the decoder assumed 0,1,2,0,… | new root attrs `epoch_pattern`, `n_epochs`, `n_patterns`, `epoch_ms`; decoder uses them and warns on old files |
| 3 | `decode_identity.py` | `--n-blocks` fixed at 14 (crash for other `--n-swr`) | defaults come from the file |
| 4 | `run.sh` | output name left out flags that change results (N_PATTERNS, HET_WCOMP, DELAY_JITTER, …) | tag every non-default value; default names are unchanged |
| 5 | `run.sh`, `replay_scaled.py` | pattern-completion mode ignored `--seed` | `--seed` is passed and used; name gets `_s<seed>` |
| 6 | `tiny.py` | missing `sinusoidal_poisson_generator` silently ran without theta / with a flat ripple | raise `RuntimeError` that names `--rhythm-gen spike_generator` |
| 7 | `replay_scaled.py` | spike_generator run past its horizon only printed a warning | HDF5 attr `rhythm_truncated` |
| 8 | `viewer/app.py` | ripple windows from `--n-swr` even without `--stc` | use the file's `n_epochs`/`epoch_ms`; without `--stc`, one epoch |
| 9 | `viewer/export_wiring.py` | node-ID check covered only CA3/CA1 | check first ID and size of every population; stop if one is missing |
| 10 | `viewer/app.py` | `run` parameter not checked; any web page could POST a launch | run names must be plain names; POST needs JSON + local Host/Origin; GET needs local Host |

Checks:
- Reference config, 1 thread: `--diff` against `s0_ref_t1.h5` lists only the 4 new attrs.
  **New S0 reference digest: `8631eb295f551caa64c316de052ca3f1235d194f8f80fd895a16c63dec472607`** (`out/s0_fix.h5`).
- Config C without `--seed`: identical to `cfgC_shim.h5`. With `--seed 303`: different, so the seed now works.
  The old config C digest (`05cc4b75…`) was made with `--seed 202` ignored; with the seed it now changes.
- Wiring export: equal to `s0_after_shim_wiring.h5`; with a wrong `--dg-scale` it stops with an error.
- Viewer: cross-site text/plain POST → 403, wrong Host → 403, `../` run name → 400.
- Generator: a missing device raises `RuntimeError`. A spike_generator run past its horizon gets `rhythm_truncated=True`.
- `run.sh` dry runs: N_PATTERNS=2 and 3 now give different names; pattern completion passes `--seed`.

Not tested: a real MPI run (no MPI here). Not fixed: `pattern_recall_specificity` (G2) and the
DG summary stats still read only local recorder events under MPI.

### 7. Does pattern identity survive to cortex? (1%, 14 blocks, 3 seeds)

Config: S0 reference flags with `--n-swr 14 --threads 3`, seeds 202/303/404 (`out/id14_s*.h5`).
Wall time: 18 min, 3 runs in parallel. Scored with `decode_identity.py --n-perm 1000`.

Home-group test (p < 0.01 = significant):

| stage | s202 | s303 | s404 |
|---|---|---|---|
| CA3 SUP | z +0.96, p 0.001 | z +0.76, p 0.001 | z +1.01, p 0.001 |
| CA1 PYR | z +0.40, p 0.002 | z +0.42, p 0.001 | z +0.52, p 0.001 |
| EC LII | z −0.04, p 0.70 | z +0.38, p 0.001 | z +0.10, p 0.16 |
| EC LV | z −0.09, p 0.75 | z +0.12, p 0.001 (5/14 blocks positive) | z −0.00, p 0.16 |
| mPFC | z −0.06, p 0.82 | z +0.04, p 0.23 | z +0.05, p 0.33 |

G1 decoder (chance 0.33): CA1 PYR above chance on all 3 seeds (best 0.71, 0.57, 0.64).
EC LII, EC LV and mPFC are at chance on all seeds.

G2 (recall after lesion): not met on any seed (specificity −0.012, −0.010, 0.000; p ≥ 0.62).
Only one assembly responds, and it is the one that also fires before the cue (spontaneous
firing), so the responses are background, not recall.

Result: **at 1%, identity is lost at the CA1 → EC LII step.** It is strong in CA3 and CA1 on
all seeds, and reaches EC LII on 1 of 3 seeds. RESULTS.md reports that EC LII carries the
code at 12% (two seeds), so 1% is a lower bound. The cortical hops are the open item.

Side note: `decode_identity.py` prints `modulation +inf%` when the off-pattern mean is 0
(s303 mPFC). Cosmetic, not fixed.

### 8. Why EC LII loses the pattern: no inhibition, so the most excitable cells always fire

Data: the 3 runs of section 7 plus their wiring exports. Scripts (local, not committed):
`out/ec_analysis/` (`ec_transfer.py`, `ec_drivers.py`, `ec_readout.py`, `ec_slice.py`).

1. **The pattern is in EC LII's input.** Input per EC LII cell = weight × CA1 spikes that
   arrive in the SWR windows. Same scorer as `decode_identity.py`:

   | seed | input z (p) | input decode | output z (p) | output decode |
   |---|---|---|---|---|
   | 202 | +0.43 (0.002) | 0.71 (p 0.008) | −0.04 (0.68) | 0.14 |
   | 303 | +0.42 (0.002) | 0.71 (p 0.010) | +0.38 (0.002) | 0.21 |
   | 404 | +0.52 (0.002) | 0.86 (p 0.002) | +0.10 (0.17) | 0.50 |

   So the loss happens inside EC LII, not on the CA1→EC wiring.
2. **Which EC LII cells fire is set by their own excitability, not by their input.**
   Spearman(total output, rheobase) = −0.73 / −0.63 / −0.70. Spearman(total output, mean CA1
   input) = +0.06 / +0.05 / +0.04. With `I_e = 0` for all cells, only 1–12% of cells ever fire:
   the CA1 volley is below threshold for a typical cell, so only the excitable tail of the
   `I_e ~ N(0, 1.5)` spread crosses it.
3. **The input changes mostly with the size of the whole burst, not with the pattern.** The
   block-to-block SD of the common input part is 5.0 / 5.4 / 11.2. The own-vs-other pattern
   difference is 1.6 / 1.3 / 1.9. CA1 burst size varies with CV 0.14–0.34.
4. **EC LII has no inhibitory input at all.** The wiring shows only `ca1_pyr` → `ec_lii`
   (50,000 synapses). Nothing can subtract the common burst size or make cells compete.

**Causal test: an EC LII "slice".** The recorded CA1 spikes of each run are replayed into a copy
of EC LII (same cells, same CA1→EC synapses, build-time weights, no STC; 2 s per run).
The slice reproduces the model: s202 36.8% of cells ever active (model 36.8%), z −0.037
(model −0.040). So STC is not the cause.

| variant (all 3 seeds) | active per block | output z | decode |
|---|---|---|---|
| model as is | 10–18% | −0.04 / +0.39 / +0.16 | 0.07 / 0.29 / 0.43 |
| weaker CA1→EC (×0.5–0.9), no inhibition | 1.5–13% | s202 stays ≤ 0; no seed decodes | 0.07–0.43, all n.s. |
| CA1→EC grouping 1.0 alone | 11–19% | +0.08 / +0.55 / +0.30 | n.s. |
| **feedforward PV inhibition, w −0.25** | 1.6–1.8% | **+0.51 / +0.48 / +0.51, all p 0.002** | **0.71 / 0.64 / 0.71, p ≤ 0.024** |
| ff inhibition −0.5 + grouping 1.0 | 2.2–2.5% | +0.60 / +0.46 / +0.59 | 1.00 / 0.57 / 0.71 |
| feedback inhibition (as built) | 9–15% | no change | n.s. |

The control matters: making EC LII equally sparse with weaker excitation does NOT bring the
pattern back. Feedforward inhibition does, on all 3 seeds. It scales with the CA1 burst, so it
removes the common part and EC LII cells compete on relative input.

Feedforward-pool settings in the slice (100 Izhikevich FS cells, CA1→PV K=200 w=0.3, PV→EC K=40)
are a first guess, not tuned. The feedback variant did not reduce activity much, so it was not
a fair test.

Biology: inhibition onto MEC LII stellate cells comes from fast-spiking PV+ interneurons, and
stellate cells interact through them (Couey et al. 2013, cited by later work). Also, CA1 and
subiculum project mainly to EC layer V, and only weakly to LII/III. The model's direct dense
CA1→EC LII projection is a simplification.

Status: slice result only, 1%. Not tested in the full model. A model change belongs in
`tinyHippo` upstream (CLAUDE.md); here it would be an opt-in flag on an experiment branch.

### 9. Feedforward inhibition in the full model (branch `ec-ff-inhibition`)

New opt-in flag `--ec-lii-ff-inhib W` (default off): a pool of N_ec/10 fast-spiking Izhikevich
cells gets CA1 PYR output (K=200, w 0.3, 1 ms) and inhibits EC LII (K=40, weight W, 1 ms).
It is wired with numpy and node-ID arrays, not NEST's RNG, so all other random streams stay the
same. The lesion also zeroes CA1→PV. Default run: digest `8631eb29…`, unchanged.

Runs: section 7 config + `--ec-lii-ff-inhib -0.25`, seeds 202/303/404 (`out/ff_s*.h5`).
Control: the section 7 runs (`out/id14_s*.h5`), same seeds.

| | control z (p) | with inhibition z (p) |
|---|---|---|
| EC LII s202 | −0.04 (0.70) | **+0.52 (0.001)**, 13/14 blocks |
| EC LII s303 | +0.38 (0.001) | **+0.41 (0.001)**, 11/14 |
| EC LII s404 | +0.10 (0.16) | **+0.31 (0.012)**, 8/14 |
| EC LV | −0.09 / +0.12 / −0.00 | −0.00 / +0.04 / +0.00 (all n.s.) |
| mPFC | −0.06 / +0.04 / +0.05 | −0.11 / −0.16 / +0.11 (all n.s.) |

- EC LII home groups now fire +160–190% more in their pattern's blocks (control +0.1–31%).
  EC LII is sparse: 1.7–2.1% active (control 11–19%).
- EC LII decoder: 0.50 / 0.64 (p 0.024) / 0.43. Weak, because the code is very sparse.
- EC LV and mPFC: still no pattern. G2: not met (specificity −0.041, −0.018; s404 skipped).
- Upstream: CA3 and CA1 unchanged. DG active 2.4–4.0% (target 2–4%). Replay over all 42
  ripples: forward ρ +0.352 → +0.331 (paired Wilcoxon p 0.93); reverse ρ −0.320 → −0.239
  (p 0.022). So reverse replay may get slightly weaker. EC LII drives DG, which drives CA3.

Result: **the CA1 → EC LII step is fixed in the full model on 3 seeds.** The loss moves one step
down, to EC LV. EC LV is 71–76% active, gets CA1 (30 inputs per cell) and EC LII (20), and has
no inhibition, the same situation EC LII was in.

1% only, one inhibition weight, pool settings not tuned.

### 10. EC LV: 27% of cells fire with no input, so the input does not matter

Data: the 3 runs with `--ec-lii-ff-inhib -0.25` (`out/ff_s*.h5`) and their wiring exports.
Scripts: `out/ec_analysis/stage_transfer.py`, `lv_slice.py`.

1. **The pattern is in EC LV's input.** From CA1: z +0.44 / +0.43 / +0.57 (p ≤ 0.004),
   decode 0.79 / 0.64 / 0.93. From EC LII: z +0.54 / +0.40 / +0.27, but EC LII is now so
   sparse that its input is about 1% of CA1's (0.4 vs 31 weight × spikes per block).
2. **EC LV output is set almost only by each cell's excitability.** Spearman(output, rheobase)
   = −0.99 on all 3 seeds. Spearman(output, mean input) = +0.01 to +0.05.
3. **Cause: EC LV gets `I_e ~ N(3.0, 1.5)`.** The mean rheobase is then 0.99, and 27% of cells
   have rheobase < 0, so they fire tonically with no input. EC LV fires at 8.3 Hz both inside
   and outside the SWR windows. (EC LII: mean rheobase 3.9, no cell below 0.)

Slice (recorded CA1 + EC LII spikes into a copy of EC LV; reproduces the model: 73.5% active,
8.3 Hz, z −0.007):

| variant | active per block | EC LV z, 3 seeds (all p) | decode |
|---|---|---|---|
| as built | 71–74% | −0.01 / +0.02 / +0.01 (n.s.) | 0.00 / 0.43 / 0.14 |
| `I_e` −2 only | 26–29% | +0.00 / +0.14 / +0.12 (mixed) | n.s. |
| ff inhibition −0.25 only | 43–44% | +0.15 / +0.13 / +0.13 (0.002) | 0.50 / 0.14 / 0.14 |
| **`I_e` −1 + ff −0.25** | 22–23% | **+0.18 / +0.17 / +0.18 (0.002)** | **0.64 (0.006) / 0.64 (0.008) / 0.43** |
| `I_e` −2 + ff −0.25 | 7.5–8% | +0.32 / +0.20 / +0.24 (0.002) | 0.71 (0.004) / 0.29 / 0.36 |

EC LV needs both changes: less tonic drive and feedforward inhibition. The signal stays weaker
than in EC LII, because EC LV's pattern input comes almost only from CA1.

**A deeper issue, found on the way: at 1% there is no CA1 burst during the SWR windows.**
CA1 PYR fires 10.0 Hz inside and 9.6 Hz outside the windows (ff_s202). In the control runs
(id14) it fires even less inside: 9.2 / 8.8 / 9.0 Hz inside vs 9.8 Hz outside. In real SWRs, CA1 pyramidal cells fire several times more than at rest. Here
the pattern is only a +6–12% change on top of a constant 10 Hz drive, so every cortical stage
has to pull a small difference out of a large constant input.

### 11. EC LV fix in the full model; mPFC loses its drive

New opt-in flags (branch `ec-ff-inhibition`): `--ec-lv-ie-shift X` (adds X to every EC LV
cell's I_e, default 0) and `--ec-lv-ff-inhib W` (feedforward PV pool onto EC LV, N_lv/10
cells, same wiring as the EC LII pool). The lesion zeroes CA1 input to both pools.

Runs: section 9 config + `--ec-lv-ie-shift -1 --ec-lv-ff-inhib -0.25`, seeds 202/303/404
(`out/lv_s*.h5`). Control: section 9 runs (`out/ff_s*.h5`).

| stage | control (ff) z | with EC LV fix (lv) z, p |
|---|---|---|
| EC LII | +0.52 / +0.41 / +0.31 | +0.48 / +0.58 / +0.47, all p 0.001 |
| **EC LV** | −0.00 / +0.04 / +0.00 (n.s.) | **+0.15 (0.003) / +0.21 (0.001) / +0.23 (0.001)** |
| mPFC | −0.11 / −0.16 / +0.11 | +0.05 / +0.06 / +0.05 (p 0.06–0.28) |

- EC LV: 21.5–22.7% active (control 71–74%). Decoder 0.43 / 0.36 / 0.57 (p 0.019 on s404).
  The slice predicted z ≈ +0.17–0.18; the full model gives +0.15–0.23.
- **mPFC is now almost silent: 1.5–1.7% active (control 32–39%).** Its only feedforward input
  is EC LV (K=20), and that drive was set for the old 73%-active EC LV. G2 is skipped on all
  seeds ("assembly too small to cue and score").

Result: the pattern now reaches EC LV on 3 seeds. The next step, EC LV → mPFC, needs its drive
re-balanced for a sparse EC LV before mPFC can be tested.

### 12. Why CA1 has no SWR burst: CA3 sits in a high, constant-drive state

Check: CA3 SUP and CA1 PYR rate inside the SWR windows vs outside, per epoch (id14 runs).
There is no burst in any epoch, also not in epoch 0, the only epoch with the SWR background:

- CA3 SUP: 19.1 / 21.7 Hz (epoch 0, inside / outside), then 20–22 / 20 Hz in every epoch.
- CA1 PYR: 10.5 / 10.4 Hz (epoch 0); over all epochs 9.0 Hz inside vs 9.8 Hz outside.

**Test 1: no theta** (new flag `--no-theta`, branch `ec-ff-inhibition`; section 7 config,
3 seeds, `out/nt_s*.h5`). Theta and SWRs do not occur together in real sleep, so theta during
the sleep epochs was a likely cause. Result: no burst either. CA3 SUP fires more without theta
(26 Hz inside and outside, vs 20 Hz), probably because theta also drove the CA3 interneurons.
CA1 10.3–10.6 inside vs 9.8–10.0 Hz outside. Replay over all ripples: forward ρ +0.28–0.30
(control +0.26–0.42), reverse −0.22 to −0.39 (control −0.29 to −0.37). So theta is not the cause.

**Cause: the constant Poisson drive onto CA3 SUP is about 14× larger than the SWR drive.**
Rate × weight per CA3 SUP cell, from `build_replay_network` defaults with `--dg`:

| drive | rate × weight (per cell, per s) | when |
|---|---|---|
| tonic (stands for EC/recurrent background) | 600 Hz × 3.0 = 1800 | always |
| EC → CA3 | 530 Hz × 2.0 = 1060 | always |
| CA3 drive | 400 Hz × 2.0 = 800 | always |
| theta (mean) | 1100 Hz × 0.8 = 880 | always |
| **sharp wave + ripple** | 280 × 0.35 + 1100 × 0.15 = **263** | epoch 0 windows only |

(The tonic and EC weights get the heterogeneity compensation `wcomp_w`, ×2.3 here, so the
constant part is even larger.) The replay trigger and scaffold are strong but brief (16 ms and
4 ms per group) and hit one group at a time.

So CA3 has no quiet baseline: it fires at ~20 Hz with 99.8% of cells active all the time, and
a "ripple" only reorders spike timing. Real CA3/CA1 pyramidal cells fire at about 1 Hz or less
in sleep and several times more during SWRs. Every downstream stage then has to read a small
pattern difference on a large constant input (sections 8–10).

Not tested: lowering the constant CA3/CA1 drive. That changes the whole hippocampal operating
point (DG, replay and STC were all calibrated at this point), so it is a science change for
`tinyHippo`, not a quick flag. (Tested later as an opt-in flag, `--ca3-drive-scale`, section 14.)

### 13. Reverse replay with EC LII inhibition: 7 seeds; inhibition sweep on the slice

Runs: section 7 config, seeds 505/606/707/808 (control `out/id14_s*.h5`, `--ec-lii-ff-inhib -0.25`
`out/ff_s*.h5`), plus seeds 202/303/404 from section 9. `id14_s909` done; `ff_s909` stopped, deleted.

| 7 seeds × 14 blocks (n = 98) | control | inhibition | paired Wilcoxon p |
|---|---|---|---|
| forward ρ | +0.330 | +0.320 | 0.88 |
| reverse ρ | −0.306 | −0.248 | **0.011** |

Reverse is weaker on 6 of 7 seeds (s707 −0.31 → −0.33). Result: **EC LII inhibition weakens
reverse replay a little (about −0.06 ρ); forward is unchanged.** Cause not checked.

Slice sweep (seeds 202/303/404, `ec_slice.py` with `win:`/`kout:` options): the result depends on
total inhibition (weight × PV inputs per cell). Weaker than −0.15 (×40): ≥ 3% active, pattern
weak or lost. −0.25: 1.6–1.8% active, z +0.48–0.51, decode 0.64–0.71 (p ≤ 0.018) on all 3.
−0.35: no better. Weak CA1→PV drive (w 0.15): worse. So −0.25 stays. Sparse code is not the
cause of the weak full-model decoder (0.43–0.64); difference to the slice not checked (STC?).

CA3 tonic drive: added by Max in 18cfbe6 (2026-08-04) on purpose (without it consolidation
failed at 12%). His comment expects CA3 ~7.5 Hz; full-loop runs show ~20 Hz. Asked him; not changed. (He
answered on 2026-11-12; the drive became an opt-in flag in section 14.)

### 14. Lower CA3 drive + stronger EC LV → mPFC: the pattern reaches mPFC on 3 seeds

Max (2026-11-12): bio plausibility is not critical, change the drive if needed. Branch `ca3-drive`.

New opt-in flags (defaults keep old behaviour):
- `--ca3-drive-scale S`: multiplies the constant Poisson inputs to CA3 (tonic, EC, drive). Default 1.
- `--swr-bg-gain G`: sharp-wave/ripple background in every epoch (default: epoch 0 only), rates × G,
  via numpy-drawn spike_generator trains. Off by default.
- `--w-eclv-mpfc W`: EC LV → mPFC weight (default 1.8 mV).

Pilot, seed 202, 6 blocks, section 11 config (`lv_s202` flags):
- Drive 1.0 / 0.7 / 0.5 / 0.35: CA3 20.6 / 14.0 / 10.1 / 7.2 Hz, but in-SWR = outside at every
  value (no burst). Pattern z downstream improves at 0.7 and 0.35 (CA1 +0.26 → +0.78 / +0.58,
  EC LV +0.04 → +0.36 / +0.24, mPFC +0.02 → +0.36 / +0.25). Replay at 0.35: +0.40 / −0.45.
- `--swr-bg-gain` 1–3: no burst. Rates in the window go DOWN (ratio 0.4–0.9): the background
  also drives CA3 and CA1 interneurons, and inhibition wins. Not used further.
- Note: 4 full runs at once filled 16 GB RAM (swap 8.3/9.2 GB) and ran ~10× slower. Use 2.
- mPFC weight at drive 0.35: w 3 / 4.5 / 6 / 9 → mPFC active in SWR 16 / 54 / 88 / 100%;
  G2 skipped / +0.024 (p 0.32) / **+0.060 (p 0.020)** / 0.000. w 9 saturates mPFC.

Confirmation, seeds 202/303/404, 14 blocks, `--ca3-drive-scale 0.35 --w-eclv-mpfc 6`
(`out/cx_s*.h5`), against section 11 (`out/lv_s*.h5`, drive 1.0, w 1.8):

| | section 11 | drive 0.35 + w 6 |
|---|---|---|
| CA1 z | +0.48 / +0.62 / +0.67 | +0.60 / +0.75 / +0.58 |
| EC LII z | +0.48 / +0.58 / +0.47 | +0.60 / +0.77 / +0.68 |
| EC LV z | +0.15 / +0.21 / +0.23 | +0.19 / +0.40 / +0.29 (all p ≤ 0.002) |
| EC LV decoder (counts) | 0.43 / 0.36 / 0.57 | **0.86 / 0.93 / 0.71** (p ≤ 0.007) |
| mPFC z | +0.05 / +0.06 / +0.05 (n.s.) | **+0.44 / +0.52 / +0.45** (p ≤ 0.002) |
| mPFC decoder (rate+timing) | 0.21 / 0.43 / 0.43 | 0.86 (p 0.001) / 0.36 / 0.71 (p 0.017) |
| G2 specificity | skipped | −0.002 (p 0.54) / +0.064 (p 0.018) / +0.011 (p 0.29) |
| replay fwd / rev | — | +0.38/−0.39, +0.31/−0.32, +0.48/−0.44 |

CA3 ~9 Hz, CA1 ~6 Hz; still no in-SWR burst (ratio 0.96–1.08).

Result: **pattern identity now reaches mPFC on all 3 seeds** (z and, on 2/3, the decoder).
**G2 is still not met** (needs p < 0.01; best +0.064, p 0.018 on s303). Two changes at once
(drive and mPFC weight), 1% only. w was picked by mPFC activity and G2 on one pilot seed.
Next: what limits G2 (mPFC recurrent learning, cue size), and a 12% check.

S0 check with all new flags off: digest 8631eb29…, same as sections 6–13. Default runs unchanged.

### 15. LLM layer, code structure and repo layout (2026-11-13, branch `llm-work`)

Branch `llm-work` = `ca3-drive` + `llm-l0` (merged clean). The fork now has only `main` and
`llm-work`; `shim`, `ec-ff-inhibition`, `ca3-drive` and `llm-l0` were fully contained and deleted.

LLM layer (`llm/`):
- No-recall threshold, L0 benchmark, tfidf, picked on seeds 0–2, checked on 3–4:

  | threshold | recall@1 (0–2 / 3–4) | false recall (0–2 / 3–4) |
  |---|---|---|
  | 0.0 (old default) | 0.78 / 0.71 | 0.92 / 0.94 |
  | 0.5 | 0.77 / 0.70 | 0.46 / 0.19 |
  | **0.6 (new default)** | 0.64 / 0.61 | 0.12 / 0.06 |
  | 0.7 | 0.47 / 0.38 | 0.00 / 0.00 |

- Bug: the stub tokenizer matched only `[a-z0-9]`, so Russian memories were never found. Fixed.
- The agent paraphrased cues ("кот любимая еда", score 0.3 < 0.6). It now cues with the
  user's own words and retries once. Live check with the API key: "what does my cat eat" found,
  "my dog's name" → "don't remember" (correct), "colour of my car" vs "blue Toyota" not found
  (no shared words; needs embeddings).
- `SlotBank` (joint plan D3-a): each memory takes the lowest free slot; slot s = model pattern s
  (`--n-patterns N --n-groups N`); `CapacityError` when full. Not wired to a model backend yet.

Model code:
- New opt-in flags: `--n-groups`, `--n-mpfc`, `--mpfc-rec-a`, `--mpfc-rec-wmax`, `--mpfc-w-ei`.
- The ~1400-line `__main__` block of `replay_scaled.py` is split into step functions
  (`build_model`, `run_consolidation`, `run_cortical_recall`, …) sharing state on `run`.
  Bit-identical to before on S0 (8631eb29…), `--pattern-completion` and `--homeostasis`.
- Regression found and fixed: `viewer/export_wiring.py` read populations from module globals,
  which moved into `main()`. `main()` now keeps its state on `replay_scaled.last_run`.
  Rebuilt wiring of `s0_fix` matches the old file in all 6.0 M connections.

Repo layout: scripts moved to `analysis/`, `plots/`, `calibration/`, `hpc/`, `legacy/`; docs to
`docs/`; images to `figures/`. 38 doc links rewritten. `check_nest.py` (NEST 2 API) and a stale
copy of `make_paper_figure.py` removed. All 19 scripts/checks ran once on real data after the move.

### 16. Capacity: 3, 10 and 30 memories (1%, seeds 202/303)

Config `cx` (section 14). One CA3 group per memory at 10 and 30 (`--n-patterns N`, and
`--n-groups 30` for 30). Blocks: 14 / 40 / 90 (≈4.7 / 4 / 3 per memory).

Pattern read off without training: in each block, the memory whose home groups fire most
(chance = 1/N):

| layer | 3 (chance 33%) | 10 (chance 10%) | 30 (chance 3%) |
|---|---|---|---|
| CA3 SUP | 100 / 100% | 100 / 100% | 98 / 99% |
| CA1 PYR | 86 / 100% | 75 / 88% | 29 / 31% |
| EC LII | 93 / 100% | 68 / 70% | 8 / 2% |
| EC LV | 64 / 79% | 30 / 38% | 6 / 6% |
| mPFC | 71 / 71% | 52 / 50% | 7 / 4% |

Cells per memory group at 30: EC LII 33, mPFC 3–4. The trained leave-one-block-out decoder
(`decode_identity.py`) agrees at 3 and 10 (EC LII 0.60–0.68, CA1 0.40–0.75 at 10) and is at
chance at 30 everywhere (only 2 training blocks per memory).

Result: **at 1%, ~10 memories reach cortex; 30 stay in the hippocampus** (CA3, CA1). Cortex
has too few cells per memory. For the LLM path at 1%: N ≤ 10, read the slot from CA1 or EC LII.
At 10 memories one group per memory means no sequence, so replay ρ is not defined.

### 17. Remote memory (G2): mPFC recurrent learning has almost nothing to learn from

Each mPFC cell: 20 recurrent inputs at 0.9 mV; Hebbian step 0.02 mV per SWR window.
Co-firing of mPFC pairs inside SWR windows (28 windows per run, ~6 of 120 cells active per
window):

| run | same-pattern pairs | other-pattern pairs | ratio |
|---|---|---|---|
| cx_s202 | 0.58 | 0.19 | 3.1 |
| cx_s303 | 0.65 | 0.19 | 3.5 |
| cx_s404 | 0.57 | 0.23 | 2.5 |

The direction is right (same-pattern pairs co-fire ~3× more), but a pair co-fires < 1 time per
run, so the learned weight change is ~0.01 mV: no assembly forms.

Variants (G2 specificity, own − others; pass = > 0 at p < 0.01):

| variant | seed 202 | 303 | 404 |
|---|---|---|---|
| baseline `cx` | −0.002 (p 0.54) | +0.064 (p 0.018) | +0.011 (p 0.29) |
| A: `--mpfc-k-rec 40 --mpfc-rec-a 0.1 --mpfc-rec-wmax 4` | +0.023 (p 0.21), mPFC fires before the cue | | |
| B: `--mpfc-w-ei 6` | +0.008 (p 0.29) | | |
| A + B | +0.012 (p 0.26) | | |
| `--mpfc-w-rec 3` | +0.030 (p 0.21) | | |
| `--mpfc-rec-a 0.3 --mpfc-rec-wmax 4` | **+0.050 (p 0.005)** | +0.023 (p 0.20) | −0.001 (p 0.55) |
| `--mpfc-rec-a 1.0 --mpfc-rec-wmax 4` | +0.044 (p 0.005), baseline not silent | | |
| `--n-mpfc 360` | −0.009 (p 0.69) | −0.012 (p 0.77) | +0.040 (p 0.0005) |

Result: **G2 not met.** The single-seed passes (rec-a 0.3 on 202, n-mpfc 360 on 404) do not
replicate; with ~13 variants tested, 1–3 chance passes are expected. mPFC 360 also does not
improve the mPFC decoder (0.57 / 0.50 / 0.79 vs 0.86 / 0.36 / 0.71). The limit is the number of
co-firing events, not the weights. Not yet tried: more sleep epochs (more SWR windows); a more
active mPFC during replay.

Open items (superseded by the list at the end of section 18):
- Remote memory (G2): more SWR windows, or more mPFC activity during replay.
- Capacity beyond 10 at 1%: more cortical cells per memory, or overlapping codes (2–3 groups
  per memory).
- `HippoBackend`, recall probe with K repeated cues, state checkpoint: after the above.

### 18. Is the cortical trace learned? No-plasticity control, a Hebbian bug, and G2 again (2026-11-13)

All runs: `cx` config (section 14), 3 memories, 14 blocks, seeds 202/303/404. Two new opt-in flags,
defaults unchanged (with the flags off the code paths are the old ones):
- `--no-stc-hook`: keep the `--stc` epoch structure, skip CA1→EC learning. With `--no-mpfc-assoc`
  this switches off all learning in the `cx` config.
- `--hebb-keep-strong`: in both mPFC Hebbian hooks, potentiation never lowers a weight.

Runs: `np_*` (no learning), `ks_*` (`--hebb-keep-strong`), `kr_*` (+ `--mpfc-rec-a 0.3
--mpfc-rec-wmax 4`), `kd_*` (+ `--mpfc-k-rec 60 --mpfc-w-rec 0.3 --mpfc-rec-a 0.1
--mpfc-rec-wmax 1.4 --g2-trials 12`). Wall time 19–38 min per batch of 3.

**1. Control without learning.** Template readout (chance 33%), cx → np:
CA1 86/100/93 → 71/86/86%, EC LII 93/100/93 → 86/86/100%, EC LV 64/79/64 → 64/79/57%,
mPFC 71/71/79 → 71/79/79%. G2 −0.002/+0.064/+0.011 → +0.070/+0.031/+0.009.
Result: **the identity seen in cortex in sections 14–17 is carried by the built-in group wiring,
not learned.** Learning added nothing measurable.

**2. Bug: the mPFC Hebbian step clamped weights DOWN.** `w = min(w + A, w_max)` with the hook's
`w_max = 2.4`, but section 14 set `--w-eclv-mpfc 6`. Every co-active EC LV→mPFC synapse was cut
from 6 to 2.4 (568/2400 in cx_s202; mean 6.0 → 5.1). Recurrent mPFC weights above 2.4 had the
same problem. With `--hebb-keep-strong` (ks): EC LV→mPFC stays at 6.0, mPFC active cells per SWR
window 6 → 19–23, recurrent own−other weight +0.022/−0.013/+0.036 mV (cx: −0.019/−0.056/−0.010).
G2 +0.052/−0.084/−0.022.

**3. Room to learn (kr).** Recurrent own−other weight **+0.29/+0.25/+0.21 mV on all 3 seeds**
(w0 2.07; 91–141 synapses at w_max). First learned, pattern-specific cortical trace in this
config. G2 −0.021/+0.017/−0.018: the cue gives a global burst, not the own assembly. Expected:
an uncued cell gets ~1.7 inputs from a 10-cell cue at K = 20 (see `--mpfc-k-rec` help), so
+0.29 mV per synapse is ~0.5 mV.

**4. Denser recurrent wiring (kd, K = 60, same total weight).** Own−other +0.044/+0.024/+0.019 mV
(≈ 4% of w0, kr ≈ 14%). G2 +0.014/+0.013/+0.020 (p ≥ 0.18). Pre-cue baseline is 0.5–0.76 of
the assembly on 2 seeds (kr_s303 too: 0.35–0.61): after the lesion the priming drive makes mPFC
fire without a cue, so the G2 test is not valid on those runs. mPFC readout dropped to 64%.

Result: **G2 still not met.** What changed: learning in mPFC now works and is pattern-specific
(kr, 3/3 seeds); before the fix it worked against the pattern. What blocks G2 at 1%: sparse
recurrent input per cue, and a priming state that is often not silent before the cue. Not fixed by learning rate or in-degree alone.

**5. Priming sweep (kr flags + `--g2-trials 12`, seed 303, `pr*_s303`).** `--cr-prime-rate`
120 (kr) / 90 / 60 / 30 Hz: pre-cue baseline 0.35–0.61 / 0.74–0.91 / 0.00–0.22 / 0.16–0.42;
G2 +0.017 / +0.001 / +0.014 / −0.014 (p ≥ 0.22). The baseline does not follow the priming.
Cause: the lesion zeroes only CA1 → cortex. EC LV keeps firing at 2.7 Hz (its own background,
section 10) and drives mPFC through the 6 mV EC LV → mPFC weights, so mPFC fires at ~1.9 Hz
before any cue. That firing carries no pattern and swamps a cue whose learned effect is
~0.5 mV per cell.

Result: **at 1%, G2 cannot be shown with these mechanisms.** The learned trace exists in the
weights (kr, 3/3 seeds), but the recall test cannot read it out: too few recurrent inputs per
cue, plus pattern-free EC LV drive after the lesion.

**6. S0 check after the new flags.** S0 config (1 thread, 4 SWR, seed 202) on `2f5887f` and on
the new code: same digest `8631eb29…`. The flags do not change the model when off. Both differ
from the 11 Nov reference `2b17274a…`; the commits merged since then (881c34e, 6b4dd16, …) caused
that, not these flags. Side note: the same config at 3 threads diverged at 3.9 s between old and
new code, which are equivalent, so 3-thread runs are probably not always bit-identical. Not
checked further.

**7. Lesion also cuts EC LV → mPFC (`--lesion-eclv-mpfc`, opt-in).** The probe comment assumes
"EC LV is silent" after the lesion; in this config it is not (item 5). The flag zeroes the 2,400
EC LV → mPFC synapses at the lesion. kr flags + `--g2-trials 12`, `lz_s*`:

| run | pre-cue baseline | G2 own − others | p |
|---|---|---|---|
| lz_s202 (learning) | 0.000 | −0.000 | 0.51 |
| lz_s303 (learning) | 0.000 | +0.025 | 0.001 PASS |
| lz_s404 (learning) | 0.000 | +0.016 | 0.001 PASS |
| lzn_s303 (no plasticity) | 0.000 | +0.033 | 0.0005 PASS |
| lzn_s404 (no plasticity) | 0.000 | +0.010 | 0.039 |

The flag fixes the baseline (0 on every run). But the no-plasticity control passes G2 as well
(s303 even higher), so **the G2 passes come from the built-in group wiring, not from sleep.**
The effect is ~1 extra cell of ~14 uncued per trial. At 1%, G2 cannot tell learned from wired.

Open items:
- Report own−other recurrent weight as the consolidation readout next to G2. G2 alone needs a
  no-plasticity control on every seed (item 7).
- 12%: run `kr` flags (`--hebb-keep-strong --mpfc-rec-a 0.3 --mpfc-rec-wmax 4`). Scale alone
  does **not** remove the 1.7-input limit: inputs per uncued cell = K × (cue size / N), and the
  cue is a fixed fraction of N. At 12% (N 1440, cue 124, K 20) it is still ~1.7. `--mpfc-k-rec`
  must rise at 12% too.
- Lesion: use `--lesion-eclv-mpfc` (item 7); the baseline problem is solved.

### 19. Pre-registration: is mPFC pattern identity after the lesion created by sleep replay? (2026-11-14)

Written before any run of this design. The pilot (below) is a feasibility check, not part of the test.

**Claim.** With random cortical wiring, the identity of a replayed pattern can be decoded from
mPFC after the hippocampal lesion, and this identity is created by SWR replay plus learning,
not by the wiring.

**Fixed config.** Section 18 `lz` flags (1%, 3 patterns, `--threads 3`, `--lesion-eclv-mpfc`,
`--g2-trials 12`, `--cr-cue-frac 0.4`) with `--cortex-group-frac 0` (random CA1→EC LV,
EC LII→EC LV, EC LV→mPFC and mPFC recurrent wiring), plus `--g2-fixed-cue --save-epoch-weights`.
Hippocampal group wiring (Schaffer, CA1→EC LII at 0.7) stays: it carries the pattern to cortex.
Input identity = the CA3 group sequence injected in each SWR (`--pattern-source ca3`;
`ca3_sup/group_ids` and `epoch_pattern` in the HDF5). There is no separate EC LII input
pattern in this mode.

**Design.**
- Learning: on (`--hebb-keep-strong --mpfc-rec-a 0.3 --mpfc-rec-wmax 4`) / off
  (`--no-stc-hook --no-mpfc-assoc`).
- Replay: intact / random. Random = each SWR drives the same number of CA3 cells with the same
  spikes, but the cells are drawn at random, not from the pattern's groups. Needs a new opt-in
  flag (not written yet; this is a model change, so it also goes to upstream `tinyHippo`).
- SWR count: 3, 6, 12, 24 (1, 2, 4, 8 replays per pattern, equal across patterns).
- Capture-blocked arm: learning on, intact replay, 12 SWR, `--prp-threshold 999`.
- 17 cells. Seeds: n = max(10, power-analysis n), same seed list in every cell, so runs pair
  by seed (same wiring).
- Changes from the original request, decided 2026-11-14: SWR levels {0, 2, 7, 14} replaced
  (0 SWR defines no mPFC assemblies to cue; 2 SWR never replays pattern 2; 7 gives 3/2/2).
  Lesion delay and criterion (d) dropped: the model has no time-dependent process between
  learning and lesion, so a delay can only mean more SWRs.

**Primary readout** (`analysis/decode_postlesion.py`). Per post-lesion cue trial: spike count of
each mPFC cell in [cue, cue + 80 ms], with every cue cell of every pattern removed (so the
decoder cannot read the cue itself). L2 logistic regression, stratified 4-fold CV × 5 repeats,
chance 1/3; null = 1000 label shuffles. Shuffle-corrected MI (bits) from the pooled confusion
matrix. Per seed: Δ = acc(learn on) − acc(learn off), same replay and SWR level. Group level:
mean Δ with a bootstrap 95% CI over seeds (10,000 resamples).

**Secondary readouts.** Recurrent own−other weight (mV). EV/REV (Kudrimoti 1999) on mPFC cell-pair
correlations of 10 ms counts: TASK = consolidation SWR windows, POST = post-lesion trials (cue
cells removed), PRE = the same seed's learning-off run POST (same wiring, no learning).
ICA assemblies (Lopes-dos-Santos 2013: Marchenko–Pastur count, FastICA patterns) from TASK,
activation strength in POST. Secondary readouts do not decide pass/fail.

**Power analysis.** From the pilot paired Δ at 12 SWR: n = ((1.96 + 0.84) · sd(Δ) / mean(Δ))²
(two-sided α 0.05, power 0.8), at least 10. If mean(Δ) ≤ 0 in the pilot, stop and report
instead of scaling.

**Exclusions** (decided now, applied blind to condition). A run is excluded if the G2 probe
skips (assembly < 4 cells) or the pre-cue baseline of any assembly is > 0.05. Excluded runs
are listed, never replaced by a new seed.

**Falsification.** The claim fails if any of these holds:
- (0) At 24 SWR, intact replay: CI of Δ includes 0 or lies below it.
- (a) Learning-off runs (any replay) or learning-on random-replay runs decode above chance:
  the bootstrap CI of the cell's mean accuracy lies above 1/3 in any of these cells.
- (b) Decoding does not rise with SWR count: Spearman ρ between SWR count and per-seed Δ
  (intact replay), bootstrap CI over seeds includes 0 or lies below it.
- (c) The capture-blocked arm keeps the trace: CI of its Δ (vs learning off, 12 SWR) lies
  above 0. Stated prediction: (c) will probably fire, because `--prp-threshold` gates only
  CA1→EC LII capture, while the post-lesion trace lives in mPFC recurrent weights, which learn
  by a Hebbian rule that capture does not gate. A fire is reported as is.

**Pilot (feasibility only).** Random wiring, intact replay, 12 SWR, seeds 202/303, learning on
(`out/idp/L_s*`) and off (`out/idp/N_s*`). Question: can learning create any decodable identity
without built-in cortical groups? Code for the pilot: opt-in `--g2-fixed-cue` (one cue subset per
pattern, exported as `g2_recall/cue_sets`) and `--save-epoch-weights` (`epoch_weights/`).

**Pilot result (2026-11-14).** 4 runs, 21–23 min each, `out/idp/`. All pre-cue baselines 0, no
exclusions. S0 check with both new flags off: digest `8631eb29…`, same as section 18 item 6.

The pre-registered readout is **not valid** and was replaced (fixed before main runs, so the
pre-registration above is superseded on this point):
- A decoder trained and tested on post-lesion trials decodes the cue in the no-learning runs
  (0.56 / 0.78, chance 0.33). A fixed cue drives the same random targets on every trial
  (N_s303: cue 0 fires one cell on 12/12 trials), so it reads "which cue", not "which memory".
- New readout: fit on the sleep SWR windows (one sample per epoch, label = replayed pattern),
  test on the post-lesion trials, all cue cells removed. Null: shuffle the **sleep** labels and
  refit. A trial-label shuffle is wrong with a fixed cue, because trials of one cue are not
  independent. This also makes G2's own p-value invalid under `--g2-fixed-cue`.

| run | responsive trials | decoder acc (null 95%) | p | G2 own−others | own−other w change, epoch 1→12 (mV) |
|---|---|---|---|---|---|
| L_s202 (learning) | 25% | 0.36 (0.44) | 0.40 | +0.026 | +0.31 |
| N_s202 (none) | 44% | 0.38 (0.46) | 0.47 | 0.000 | — |
| L_s303 (learning) | 17% | 0.28 (0.39) | 1.00 | 0.000 | +0.18 |
| N_s303 (none) | 53% | 0.52 (0.63) | 0.28 | +0.006 | — |

1. **No learning effect after the lesion.** All 4 runs decode at chance. Δ (learning − none):
   decoder −0.02 / −0.24, G2 +0.026 / −0.006.
2. **Learning changes weights on both seeds by a similar amount** (+0.31 / +0.18 mV). Use the
   change, not the final value: with `--het 0.30` and only 11–25 synapses inside the assemblies,
   the random starting offset is ±0.15 mV (seen: +0.20 / −0.16 after epoch 1).
3. **Cause: the input to mPFC is not selective.** With random cortical wiring, mPFC fires almost
   the same cells for every pattern during sleep (Jaccard of active sets: same pattern 0.44–0.58,
   different patterns 0.51–0.52). The assemblies (5–7 cells) are picked mostly from noise.
4. **Little to read after the lesion:** only 3–6 non-cue mPFC cells fire, on 17–53% of trials.

Result: at 1% with random cortical wiring the trace fails at the input, not at learning. Stop
rule met (decoder mean Δ ≤ 0): **not scaled.**

### 20. Can G2 detect a cortical trace of the size sleep learning makes? (2026-11-14)

**Pre-registration** (written before any Test A or B run).

Question: the §19 pilot learned +0.18 / +0.31 mV own−other recurrent weight and G2 saw nothing.
Is G2 too weak to see a trace of that size? If so, a G2 null (1% or 12%) says nothing about sleep.

Already done, not repeated: no-learning twins and `--lesion-eclv-mpfc` (§18), cortex-group-frac
0 and 0.7 with learning on/off (§18, §19), sleep-trained decoder (§19).

New opt-in code (S0 digest must stay `8631eb29…` with it off):
- `--plant-trace DW`: after the G2 assemblies are chosen and before the first cue, add DW mV to
  every recurrent mPFC synapse whose pre and post cells are in the same assembly. Test only.
  The weights are read back and checked. Count in `g2_recall` attr `n_planted`.
- `--save-epoch-weights` also saves `epoch_weights/mpfc_rec_pre` (before any learning).

Config: §19 pilot flags (12 SWR, 3 patterns, `--threads 3`), **without** `--g2-fixed-cue`. G2 uses
the default random cue subset per trial, so its trial-shuffle null is the one H17 uses.
The §19 decoder is dropped here: it needs `--g2-fixed-cue`, and a fixed cue breaks G2's null.

- **Test A:** learning off, cortex-group-frac 0, DW ∈ {0, 0.1, 0.3, 0.5, 1.0}, seeds 202/303/404
  (15 runs). Detected = G2 specificity > 0 at p < 0.01 on ≥ 2 of 3 seeds. Output: the smallest
  detected DW, plus mean specificity per DW.
  Validity check: a DW = 0 run with p < 0.01 means the null is too narrow; report it.
  Stop rule: if DW = 0.5 is not detected, skip Test B and report that G2 cannot test the claim.
- **Test B (optional):** cortex-group-frac 0.2 and 0.4 × learning on/off × seeds 202/303/404
  (12 runs). Per seed: Δ = learning − no learning for G2 specificity; own−other weight change
  (final − pre) for learning runs. Bootstrap 95% CI over seeds.

Known caveat: 3-thread runs repeat in mPFC and in sleep (2 identical runs, 0 differences), but
the hippocampus diverges after sleep (~3084 ms), and one earlier smoke run picked different
assemblies (9 vs 4 cells) with the same config; that run could not be rechecked. Seeds, not
reruns, are the unit of replication.

**Result, Test A (15 runs, `out/pt/A_dw*_s*.h5`): G2 detects no planted trace, even 1.0 mV.**

G2 specificity (p), from `g2_recall` attrs. Planted synapse count in brackets.

| DW mV | s202 | s303 | s404 |
|---|---|---|---|
| 0   | +0.0045 (0.23) [0]  | +0.0019 (0.38) [0]  | 0 (1.0) [0] |
| 0.1 | +0.0027 (0.32) [38] | −0.0218 (1.0) [24]  | −0.0042 (1.0) [47] |
| 0.3 | −0.0013 (1.0) [52]  | +0.0019 (0.38) [43] | −0.0046 (1.0) [77] |
| 0.5 | +0.0045 (0.22) [63] | 0 (1.0) [12]        | 0 (1.0) [80] |
| 1.0 | +0.0106 (0.036) [38]| −0.0006 (0.62) [37] | +0.0130 (0.14) [35] |

1. No run reaches p < 0.01, so no DW is detected. The smallest detected DW does not exist in 0–1.0 mV.
2. Validity check passes: no DW = 0 run has p < 0.01.
3. Stop rule met (0.5 mV not detected). Test B not run.
4. Conclusion: at 1%, G2 cannot see a recurrent mPFC trace 3–5× larger than the one §19 learning
   made. A G2 null at 1% therefore says nothing about sleep consolidation.
5. Side finding: assembly size changes between runs of the same seed (s303: 5–10 cells; s404: 9–12)
   although the assemblies are chosen before the plant. This matches the §20 caveat on 3-thread runs.
   Small assemblies (5 cells, 12 planted synapses) give G2 even less to read.

Not tested: whether G2 detects a trace at 12% (more recurrent inputs per cell), or with a larger DW.

### 21. LLM step 3a: memories from the Nous database as EC LII spikes (2026-11-18)

Task from Max: (3a) show database memories as spike sequences in EC, (3b) run consolidation,
(3c) read the consolidated associations from EC. Option A first: a memory takes one model slot
(`SlotBank`), slot s = pattern s; the text does not shape the spikes.

New code (S0 digest with the flag off: `8631eb29…`, unchanged):
- `llm/nous_export.py`: read-only export of active facts (oldest first, category `rule` skipped)
  from the Nous eval database (`nous_mab_wp`, over Tailscale), with slots. Output in `out/nous/`
  (not committed: it holds database text). Agent `mab-eval-prod_memory-8f18622a`, 3 facts:
  0 "Glenn L. Martin Company was founded by Glenn L. Martin", 1 "Ian Marter died in the city of
  London", 2 "Katniss Everdeen was created by Suzanne Collins".
- `--ec-memories FILE` (opt-in, needs `--pattern-source ec-lii`, n_slots = `--n-patterns`): saves
  slot/id/text in HDF5 group `ec_memories`. The EC LII drive itself is the existing place-field drive.
- `plots/plot_ec_memories.py`: EC LII raster per memory, cells sorted by home memory.

Config: §18 `kr` flags (cx + learning) with `--pattern-source ec-lii --place-field-sigma 0.15
--ec-pattern-base-rate 20 --ec-pattern-peak-rate 800 --ec-pattern-weight 1.5
--dg-ec-cluster-sigma 0.05` (Max's JOB H8 values), 12 SWR. `em3` = no extra routing; `emr` = +
JOB H16 routing (`--mf-group-frac 0.7 --ec-ca3-k 12 --ec-ca3-w 1.0 --ec-ca3-group-frac 0.7`).

| run | EC LII z (decoder) | CA3 SUP z | CA1 z | EC LV z (decoder) | mPFC z |
|---|---|---|---|---|---|
| em3_s202 | +1.41 (1.00, p 0.0005) | +0.07 (p 0.16) | −0.05 | +0.07 (0.00) | −0.09 |
| emr_s202 | +1.41 (1.00, p 0.0005) | +0.09 (p 0.24) | +0.13 (p 0.20) | −0.03 (0.08) | −0.21 |
| emr_s303 | +1.37 (1.00, p 0.0005) | +0.18 (p 0.07) | +0.12 (p 0.27) | +0.10 (0.58, p 0.02) | −0.06 |

Result: **3a works at the input**: each memory drives its own EC LII band (raster
`out/em/em3_s202_raster.png`). **It does not reach the hippocampus**: CA3 stays at chance, so
nothing downstream can be consolidated. This repeats upstream RESULTS.md §31; the §32 routing
(CA3 z +0.42 there) gives only +0.09/+0.18 here. Not checked: why weaker than §32 (12 vs 14
blocks, `--ca3-drive-scale 0.35`, the cx cortex flags). 3b/3c not run: with CA3 at chance they
would only measure the wiring.

**Hybrid (`--pattern-source both`, new choice).** Both drives at once: the ec-lii place-field
drive on EC LII (the database memory, 3a) and the ca3 trigger/scaffold on CA3. So the
hippocampal pattern comes from the CA3 drive, not from the EC input (EC → CA3 fails at 1%,
above). 3b/3c therefore test consolidation of an already-encoded memory, not encoding.
Control `hyoff`: the same run with `--ec-pattern-weight 0` (EC drive off). Same flags as `em3`
otherwise, without `--dg-ec-cluster-sigma`. S0 with the new code: `8631eb29…`, unchanged.

| run | CA3 z | CA1 z (dec) | EC LII z (dec) | EC LV z (dec) | mPFC z (dec) | G2 (p) |
|---|---|---|---|---|---|---|
| hy_s202 | +1.10 | +0.73 (0.75) | +1.39 (1.00) | +0.44 (0.67) | +0.52 (0.58) | +0.008 (0.011) |
| hy_s303 | +1.07 | +0.49 (0.75) | +1.36 (1.00) | +0.42 (0.92) | +0.41 (0.92) | 0.000 (1.0) |
| hyoff_s202 | +1.07 | +0.81 (0.75) | +0.80 (1.00) | +0.46 (0.83) | +0.60 (0.75) | +0.100 (0.0005) |
| hyoff_s303 | +1.05 | +0.55 (0.50) | +0.46 (0.67) | +0.21 (0.42) | +0.34 (0.67) | +0.012 (0.04) |

z: all p ≤ 0.0005. Decoder = rate+timing accuracy, chance 0.33.

Result: **in the hybrid, the database memories reach CA3, CA1, EC LV and mPFC on both seeds.**
As expected, this comes from the CA3 drive: with the EC drive off, every stage still carries
the memory. The EC input adds identity mainly in EC LII itself (z +1.39/+1.36 vs +0.80/+0.46)
and, on s303 only, in EC LV (+0.42 vs +0.21). G2 passes only on `hyoff_s202`, without EC input,
so G2 says nothing about the EC input (and §20: G2 cannot see a trace at 1%).
Not done: 3c (associations read from EC after the lesion, against a no-learning twin).

**3c: is the memory in EC learned? (hybrid, learning vs no-learning twin).** `hyL` = the hybrid
flags (`out/em/hy.base`), rerun so the file has the new `stc/pre_gid`; `hyN` = the same plus
`--no-stc-hook --no-mpfc-assoc` (no plasticity anywhere). Seeds 202 and 303. New readout
`analysis/ec_weight_readout.py`: the learned CA1 → EC LII weight change, own memory minus other
memories (pre label = CA1 index % G, post label = EC LII `home_group`; null = permute the EC home
labels, 2000 times). `stc/pre_gid` is saved only with `--ec-memories`; S0 `8631eb29…`, unchanged.

| run | EC LII z (dec) | EC LV z (dec) | mPFC z (dec) | G2 (p) | CA1→EC LII own−other Δw (p) |
|---|---|---|---|---|---|
| hyL_s202 | +1.39 (1.00) | +0.45 (0.83) | +0.36 (0.83) | +0.043 (0.0005) | +0.0011 mV (0.17) |
| hyN_s202 | +1.38 (1.00) | +0.41 (0.83) | +0.49 (1.00) | +0.031 (0.0005) | 0 (no learning) |
| hyL_s303 | +1.36 (1.00) | +0.46 (0.92) | +0.43 (1.00) | +0.015 (0.004) | +0.0015 mV (0.066) |
| hyN_s303 | +1.37 (1.00) | +0.40 (1.00) | +0.49 (0.83) | +0.009 (0.016) | 0 (no learning) |

z: all p ≤ 0.0005. Decoder = rate+timing accuracy, chance 0.33. Mean CA1 → EC LII Δw is
+0.004 mV on w_init 0.30 (about 1.4%); L-LTP fraction own 0.019/0.014 vs other 0.021/0.013.

Result: **no learned association in EC at 1%.** Learning and no-learning twins are equal in EC
LII, EC LV and mPFC (differences ≤ 0.13 z, both directions). The learned CA1 → EC LII weights
change by about 1% and are not memory-specific (p 0.17 and 0.07). So the memory identity seen
in EC comes from the drive and the group wiring, not from consolidation (as WORKLOG §18).
G2 passes in the no-learning twin `hyN_s202` (p 0.0005): G2 here also measures wiring.
Not checked: a post-lesion recall probe in EC itself (the probe cues mPFC only); 12%.

## 22. Sleep learning without the wiring shortcut: gate fixed before the runs (2026-11-18)

Question: does sleep (STC + mPFC Hebbian) put memory-specific weights into cortex when the
wiring gives cortex no identity? §21: with group wiring, learning added nothing measurable.

Config: the §21 hybrid flags (`out/em/hy.base`) with `--ca1-ec-group-frac 0 --cortex-group-frac 0`
(CA1 → EC LII, CA1 → EC LV, EC LII → EC LV, EC LV → mPFC uniformly random). `rwL` = learning on;
`rwN` = the same plus `--no-stc-hook --no-mpfc-assoc`. Seeds 202, 303. Nothing else changes.

Gate (written before any `rw` run):
1. Readout validity (positive control, done on `hyL_s202/303`): `ec_weight_readout.py --plant`
   detects a planted own-synapse trace of 0.002 mV (0.7% of w_init) at p 0.0025 / 0.0005;
   a random plant of 0.01 mV gives p 0.18 / 0.06 (fails, as it must). **PASS.**
   (G2 could not see 1.0 mV, §20, so G2 is not a gate here.)
2. Shortcut removed (validity): in `rwN`, EC LV and mPFC home-group z has p ≥ 0.01 on both seeds.
   If not, the wiring still carries identity and the run does not test learning.
3. **Primary: learning happens and is memory-specific** = in `rwL`, CA1 → EC LII own−other Δw
   > 0 with p < 0.01 on both seeds. Fail on either seed = no specific sleep learning.
4. Secondary (descriptive, no gate): decoder accuracy in EC LII, EC LV, mPFC, `rwL` vs `rwN`;
   G2.

Prediction (before the runs): gate 3 fails. Reason: CA1 PYR fires on almost every ripple
(CLAUDE.md), so CA1 → EC co-activity does not depend on the memory (§21: L-LTP own 0.019 vs
other 0.021).

Result (runs 19:09–19:46, about 18 min each, 2 in parallel):

| run | CA1 z | EC LII z (dec) | EC LV z (p) (dec) | mPFC z (p) (dec) | G2 (p) | CA1→EC LII own−other Δw (p) |
|---|---|---|---|---|---|---|
| rwL_s202 | +0.65 | +1.41 (1.00) | −0.09 (0.82) (0.25) | −0.05 (0.74) (0.17) | −0.003 (0.70) | −0.0002 mV (0.69) |
| rwN_s202 | +0.67 | +1.41 (1.00) | −0.05 (0.55) (0.42) | −0.02 (0.48) (0.33) | −0.002 (0.73) | 0 (no learning) |
| rwL_s303 | +0.59 | +1.37 (1.00) | −0.12 (0.96) (0.50) | −0.02 (0.33) (0.08) | +0.000 (1.0) | −0.0005 mV (0.97) |
| rwN_s303 | +0.66 | +1.36 (1.00) | −0.10 (0.91) (0.42) | −0.07 (0.50) (0.08) | +0.017 (0.04) | 0 (no learning) |

dec = rate+timing decoder accuracy, chance 0.33. Null SD of the weight readout here: 0.0003 mV
(smaller than in §21, so this test is more sensitive). Mean Δw +0.003 mV (1% of w_init);
L-LTP own 0.016/0.017 vs other 0.017/0.021.

Gate:
1. Readout validity: PASS (above).
2. Shortcut removed: **PASS.** `rwN` EC LV and mPFC z p ≥ 0.48 on both seeds.
3. Primary: **FAIL on both seeds** (own−other Δw −0.0002 / −0.0005 mV, p 0.69 / 0.97).
   The prediction held.

Result: **sleep produces no memory-specific learning at 1%.** The weights change by about 1%,
and own and other memories get the same change (other even slightly more). Without the group
wiring, cortex loses all identity: EC LV and mPFC are at chance in the decoder too, in both
learning and twin runs, although EC LII decodes at 1.00. So two things are missing:
(a) a learning signal that depends on the memory (likely cause: CA1 fires on almost every
ripple, path 2), and (b) transmission from EC LII to EC LV through random wiring.
Not checked: (b)'s cause; CA1 active fraction per ripple (path 2 measures it first).

## 23. Path 2: a sparse CA1 during ripples, so sleep learning can be memory-specific (2026-11-18)

Measured first (§22 runs, SWR windows, cell active = ≥ 1 spike): CA1 PYR is active 0.67 / 0.53
per ripple (`rwL_s202/303`; min 0.26). Own-memory cells 0.71 vs other 0.65 (s202), 0.59 vs 0.50
(s303): only 1.1–1.2×. So CA1 → EC co-activity barely depends on the memory.

Risk found in the code (`run_stc_hook`): the rule is pair STDP on the LAST spike of each cell in
the window (dt = t_post − t_pre − delay; sign sets LTP or LTD). EC LII spikes come mostly from
its own place-field drive, not from CA1, so the sign may be random for own and other synapses
alike. Then a sparse CA1 alone will not help, and the rule must change (path 3).

Knob: `--schaffer-w-scale S` (exists; scales CA3 → CA1 PYR only, CA1 basket drive unchanged).

Sweep (step A): `rw` config, learning on, seed 202, `--n-swr 6`, S ∈ {1.0, 0.7, 0.5, 0.35}.
Gate fixed before the runs:
1. Sparsity: pick the largest S with CA1 active 0.10–0.30 per ripple and own/other ≥ 2.
   If no S reaches this, path 2 with this knob fails; next = a CA1 inhibition knob.
2. Replay intact: CA3 home-group z at that S within 0.2 of S = 1.0.
3. Primary (step B, full 12 SWR, seeds 202 + 303, learning vs twin): same as §22 gate 3,
   CA1 → EC LII own−other Δw > 0 at p < 0.01 on both seeds.
Prediction: gate 1 can pass; gate 3 fails because of the STDP timing risk above.

Step A result (seed 202, 6 SWR, learning on; runs 19:56–20:28):

| S | CA1 active / ripple (min) | own | other | own/other | CA3 z | CA1 z | own−other Δw (p) |
|---|---|---|---|---|---|---|---|
| 1.0 | 0.63 (0.33) | 0.68 | 0.60 | 1.13 | +1.17 | +0.72 | +0.046 µV (0.056) |
| 0.7 | 0.32 (0.10) | 0.37 | 0.29 | 1.28 | +1.18 | +0.46 | +0.086 µV (0.0015) |
| 0.5 | 0.22 (0.04) | 0.29 | 0.19 | 1.55 | +1.10 | +0.66 | +0.068 µV (0.005) |
| 0.35 | 0.12 (0.01) | 0.14 | 0.11 | 1.29 | +1.10 | +0.53 | −0.007 µV (0.70) |

(`ec_weight_readout.py` now prints µV.) Mean Δw only +0.1–0.3 µV: with 6 SWR (12 events) no
synapse reaches L-LTP (`--prp-threshold 14`), so this is E-LTP STDP only.

Gate:
1. Sparsity: **FAIL as written.** The 0.10–0.30 range is reached (S 0.5 and 0.35), but own/other
   never reaches 2 (max 1.55 at S 0.5).
2. Replay intact: PASS at all S (CA3 z 1.10–1.18).
3. Not run (gate 1 failed).

Result: **a sparser CA1 does make sleep learning memory-specific, but the effect is tiny.**
At S 0.7 and 0.5 own−other Δw is significant (p 0.0015, 0.005); at S 1.0 it is not (p 0.056).
My prediction (STDP sign random → no specificity) was wrong in direction, right in size: the
effect is +0.07–0.09 µV, about 0.03% of w_init (300 µV); one seed, 6 SWR.
Why own/other stays ≤ 1.55: sparsity is not the limit. A CA1 cell gets only 70% of its Schaffer
inputs from its home group (`--schaffer-group-frac 0.7`), so it also fires for other memories.
At S 0.35 selectivity drops again (too few spikes). Not checked: other seeds; 12 SWR.

Step A2 (gate fixed before the runs): raise CA3 → CA1 grouping. Same as step A at S 0.5
(seed 202, 6 SWR, learning on), with `--schaffer-group-frac` 0.9 and 1.0 (was 0.7).
Gate: the step A gate 1 (CA1 active 0.10–0.30, own/other ≥ 2) and gate 2 (CA3 z within 0.2 of
step A S 1.0, +1.17). If a value passes, step B (12 SWR, 2 seeds, learning vs twin) uses it.
Prediction: own/other rises above 2 at 1.0; own−other Δw stays below 1 µV (no L-LTP in 6 SWR).

Step A2 result: **no effect, by construction.** `sg09`/`sg10` give exactly the `sw050` numbers.
Cause (log + `ca3_sup/group_ids` (10, 264)): a CA3 group has 264 cells, and `grouped_fixed_connect`
clamps k_home to the group size. With `--schaffer-k 500`, a CA1 cell already takes all 264 home
cells at frac 0.7 (target 350). So **the real home share is 264/500 = 53% at any frac ≥ 0.53**,
not 70% as the flag suggests (also for DEEP: 66/125). Earlier WORKLOG text that says "70% home"
for Schaffer at 1% is wrong in the same way.

Step A3 (gate fixed before the runs): lower the in-degree so the home share rises:
`--schaffer-k 300 --schaffer-group-frac 1.0` (home 264/300 = 88%) and `--schaffer-k 264
--schaffer-group-frac 1.0` (100%). Weights scale by K_default/K, so the mean drive is kept.
S 0.5, seed 202, 6 SWR, learning on. Same gate as A2.

Step A3 result:

| run | home share | CA1 active (min) | own | other | own/other | CA3 z | own−other Δw (p) |
|---|---|---|---|---|---|---|---|
| sw050 (k 500) | 53% | 0.22 (0.04) | 0.29 | 0.19 | 1.55 | +1.10 | +0.068 µV (0.005) |
| sk300 | 88% | 0.17 (0.06) | 0.26 | 0.12 | 2.11 | +1.03 | +0.153 µV (0.0005) |
| sk264 | 100% | 0.16 (0.05) | 0.26 | 0.12 | 2.26 | +1.17 | +0.215 µV (0.0005) |

Gate: **PASS for both** (active 0.10–0.30, own/other ≥ 2, CA3 z within 0.2 of +1.17).
Specificity of the weight change rises with CA1 selectivity (0.07 → 0.15 → 0.22 µV), but it
is still about 0.07% of w_init: 6 SWR, no L-LTP. Step B uses `sk264`
(`--schaffer-w-scale 0.5 --schaffer-k 264 --schaffer-group-frac 1.0`): best ratio, CA3 intact.

Step B (gate = step A gate 3, fixed above): `rw` config + the sk264 flags, 12 SWR, seeds 202 and
303, learning (`p2L`) vs twin (`p2N`, `--no-stc-hook --no-mpfc-assoc`). Descriptive: L-LTP own
vs other, EC LV / mPFC decoder vs twin.

Step B result (runs 20:54–21:37):

| run | CA1 active | own/other | EC LV dec | mPFC dec | G2 (p) | own−other Δw (p) | L-LTP own / other |
|---|---|---|---|---|---|---|---|
| p2L_s202 | 0.16 | 2.06 | 0.58 | 0.33 | +0.045 (0.0005) | +0.468 µV (0.0005) | 0.007 / 0.007 |
| p2N_s202 | 0.18 | 2.15 | 0.33 | 0.42 | +0.016 (0.045) | 0 | — |
| p2L_s303 | 0.18 | 2.47 | 0.33 | 0.50 | +0.023 (0.035) | +0.417 µV (0.0125) | 0.006 / 0.007 |
| p2N_s303 | 0.21 | 2.16 | 0.08 | 0.42 | +0.033 (0.0035) | 0 | — |

dec = rate+timing decoder, chance 0.33. CA3 z +1.09–1.15, EC LII z +1.37–1.41 (all p 0.0005);
EC LV and mPFC home-group z ≈ 0 (p ≥ 0.24) in all four runs.

Gate 3: **FAIL, narrowly.** s202 p 0.0005; s303 p 0.0125 (> 0.01). Fixed rule: fail on either seed.

Result: with a selective CA1, sleep learning is memory-specific in direction on both seeds
(+0.47 / +0.42 µV, 7× the step A size), but it is small (0.15% of w_init; mean Δw +1.1–1.4 µV)
and does not reach cortex (EC LV, mPFC decoders and z at chance, learning = twin; G2 mixed).
**L-LTP capture is not specific (own 0.007 = other 0.007)**, so all specificity comes from E-LTP.
Likely cause, from `run_stc_hook`: the tag is set from |Δw|, so an LTD pairing also tags a
synapse, and capture then raises it × 1.3. (A second cause written here first, "every EC LII
cell fires in every ripple", was wrong: see §24.) Not checked directly. This is path 3.

## 24. Path 3: make L-LTP capture memory-specific (2026-11-19)

Data first (`p2L_s202`, `stc/`): 57–91 of 1000 EC LII cells fire per ripple event (6–9%), not
all. Only 2.1% of EC cells reach the PRP threshold (`--prp-threshold 14`; median pool 0). Capture
starts at event 16 of 24. With 3 memories, a memory gets 8 of the 24 events (4 epochs × fwd+rev),
so **a cell that fires only for its own memory can never reach 14**. Only cells that fire for
several memories can capture: the least specific ones. This is a second cause, next to the tag
sign (§23).

Two changes, tested separately and together:
1. New opt-in flag `--stc-ltp-tag-only`: the tag is set only by an LTP pairing (Δw ≥ tag
   threshold). Default off: the old |Δw| rule, so S0 is unchanged.
2. `--prp-threshold 6` (existing flag; ≤ 8, so a cell selective for one memory can capture).

Config: §23 step B (`rw` + `--schaffer-w-scale 0.5 --schaffer-k 264 --schaffer-group-frac 1.0`),
12 SWR, seeds 202 and 303. Twins = `p2N_s202/303` (no plasticity: the new flags change nothing
there). Runs: `p3T` = change 1; `p3TP` = changes 1 + 2.
Gate (fixed before the runs), per variant:
1. Primary: CA1 → EC LII own−other Δw > 0 at p < 0.01 on both seeds.
2. Capture is specific: L-LTP fraction own > other on both seeds.
3. Size: own−other Δw ≥ 10× the §23 step B value (≥ 4 µV) on both seeds.
4. Descriptive: EC LV, mPFC decoder vs twin; G2.
Prediction: `p3T` passes 1 but not 2 or 3 (few cells reach PRP 14); `p3TP` passes 1–3.

Result (runs 11:29–12:03; S0 after the new flag: `8631eb29…`, unchanged):

| run | own−other Δw (p) | L-LTP own / other | cells ≥ PRP thr | L-LTP synapses | mPFC z (p) | G2 (p) |
|---|---|---|---|---|---|---|
| p2L_s202 (§23, old rule) | +0.47 µV (0.0005) | 0.007 / 0.007 | 0.021 | — | −0.01 (0.58) | +0.045 (0.0005) |
| p3T_s202 | +0.32 µV (0.0005) | 0.004 / 0.005 | 0.019 | 240 | −0.01 (0.55) | −0.002 (1.0) |
| p3T_s303 | +0.46 µV (0.0015) | 0.004 / 0.005 | 0.019 | 240 | −0.10 (0.93) | +0.000 (1.0) |
| p3TP_s202 | +1.22 µV (0.0005) | 0.038 / 0.031 | 0.139 | 1670 | +0.14 (0.0015) | +0.036 (0.001) |
| p3TP_s303 | +2.34 µV (0.0005) | 0.030 / 0.017 | 0.135 | 1066 | −0.05 (0.44) | −0.004 (1.0) |

CA3 z +1.09–1.15 and EC LII z +1.37–1.41 in all runs (p 0.0005). EC LV home z ≈ 0 and EC LV
decoder at chance (0.17–0.42) in all runs; mPFC decoder 0.25–0.58.

Gate:
- `p3T` (LTP-only tag): 1 PASS; 2 FAIL (own 0.004 < other 0.005); 3 FAIL (0.3–0.5 µV).
- `p3TP` (LTP-only tag + PRP 6): 1 PASS; **2 PASS** (own 0.038 > 0.031, 0.030 > 0.017);
  3 FAIL (1.2 / 2.3 µV, target ≥ 4 µV).
Prediction: right for `p3T`; for `p3TP` right on 1–2, wrong on 3 (size).

Result: **with both fixes, capture itself becomes memory-specific on both seeds, and the specific
weight change is 3–5× the §23 value** (+1.2 / +2.3 µV, 0.4–0.8% of w_init). It is still small,
and it still does not reach cortex: EC LV is at chance in every run, and the one mPFC signal
(`p3TP_s202` z +0.14, G2 p 0.001) does not replicate on s303.
Odd, not checked: `p3T` has exactly 240 L-LTP synapses on both seeds.
Open: the size limit (capture × 1.3 on 3% of synapses, w_max 1.5 × w_init) and the
EC LII → EC LV transfer (§22 (b)), which blocks any cortical readout.

## 25. Why EC LII does not reach EC LV (diagnosis, 2026-11-19)

Measured: fraction of cells with ≥ 1 spike, ripple windows (300–420, 600–720 ms) vs equal
windows outside ripples (100–220, 850–970 ms), mean over 24 windows.

| run | CA1 in / out | EC LII in / out | EC LV in / out | EC LV rate in / out |
|---|---|---|---|---|
| rwL_s202 (§22) | 0.67 / 0.46 | 0.077 / 0.004 | 0.185 / 0.166 | 2.4 / 2.3 Hz |
| p3TP_s202 (§24) | 0.17 / 0.17 | 0.070 / 0.002 | 0.157 / 0.152 | 2.2 / 2.1 Hz |
| p3TP_s303 (§24) | 0.16 / 0.11 | 0.067 / 0.001 | 0.149 / 0.141 | 2.1 / 2.0 Hz |
| hyL_s202 (§21, grouped) | 0.54 / 0.38 | 0.085 / 0.003 | 0.192 / 0.161 | 2.5 / 2.2 Hz |

Result: **EC LV does not respond to ripples.** It fires the same in and out of ripples
(+1–3 points), so its spikes come from its own drive (I_e ~ N(3, 1.5) − 1), not from EC LII.
Estimated ripple volley per EC LV cell (in-degree × active fraction × weight, defaults in
`build_ec_lv`): EC LII 20 × 0.07 × 0.8 mV ≈ 1.1 mV; CA1 30 × 0.17 × 0.45 mV ≈ 2.3 mV
(p3TP; ≈ 9 mV at CA1 0.67). The rest-to-threshold gap is 15–24 mV (code comment). So the
EC LII share is about 1 mV, 15–20× below threshold: EC LII is sparse (7% per ripple), and
K 20 × 0.8 mV cannot carry a sparse code. With group wiring (`hyL`), the small bias was enough
for EC LV z +0.45; with random wiring it is lost in the intrinsic firing.
Not checked: the real volley (V_m recordings); why CA1 in `p3TP_s202` is not ripple-locked
(0.17 / 0.17; s303 is: 0.16 / 0.11).
Fix candidates (none run): an opt-in EC LII → EC LV weight / in-degree (no flag exists now), so
that one memory's EC LII cells sum to near threshold; or less intrinsic EC LV drive
(`--ec-lv-ie-shift`, exists), so ripple input stands out.

Sweep (gate fixed before the runs). New opt-in flags `--w-eclii-lv W`, `--eclii-lv-k K`
(default: the build values 0.8 mV, 20). Config: `p3TP` (§24: `rw` + sk264 flags +
`--stc-ltp-tag-only --prp-threshold 6`), 12 SWR, seed 202, learning on. `--eclii-lv-k 60` and
W ∈ {1.6, 2.4, 3.2, 4.0} mV: estimated EC LII volley 60 × 0.07 × W ≈ 6.7, 10, 13, 17 mV
(reference: `p3TP_s202`, K 20, W 0.8, ≈ 1.1 mV).
Gate:
1. Ripple-locked: EC LV active in ripple − out ≥ 0.05.
2. Not saturated: EC LV active in ripple ≤ 0.40.
3. Identity reaches EC LV: EC LV decoder (rate+timing or counts) p < 0.01.
Pick the smallest W that passes 1–3. That W then needs seed 303 and a learning vs twin test
(not part of this sweep). Descriptive: mPFC decoder, CA3/EC LII z (must stay as in p3TP).
Prediction: 1–2 pass from W 2.4; 3 passes at W ≥ 2.4 (a random projection of a 7%-sparse code
with 60 inputs carries the memory).

Sweep result (runs 18:55–19:30; S0 after the new flags: `8631eb29…`, unchanged):

| W (mV) | EC LV active in / out | EC LV dec r+t / counts (p) | mPFC active in / out | mPFC dec r+t / counts (p) | G2 (p) | own−other Δw (p) |
|---|---|---|---|---|---|---|
| 0.8, K 20 (`p3TP_s202`) | 0.157 / 0.152 | 0.42 / 0.08 (0.11 / 0.90) | — | 0.25 / 0.00 | +0.036 (0.001) | +1.22 µV (0.0005) |
| 1.6 | 0.211 / 0.151 | 0.58 / 1.00 (0.0035 / 0.0005) | 0.211 / 0.116 | 0.33 / 0.42 (0.32 / 0.18) | +0.014 (0.029) | +2.68 µV (0.0005) |
| 2.4 | 0.280 / 0.149 | 1.00 / 1.00 (0.001 / 0.0005) | 0.430 / 0.111 | 0.83 / 0.50 (0.001 / 0.038) | +0.018 (0.006) | +2.39 µV (0.0005) |
| 3.2 | 0.343 / 0.152 | 1.00 / 1.00 (0.001 / 0.0005) | 0.543 / 0.111 | 0.67 / 0.92 (0.016 / 0.0005) | +0.015 (0.036) | +2.21 µV (0.0005) |
| 4.0 | 0.434 / 0.151 | 0.92 / 1.00 (0.001 / 0.0005) | 0.689 / 0.110 | 0.67 / 0.67 (0.016 / 0.007) | +0.003 (0.28) | +2.98 µV (0.0005) |

K 60 for W 1.6–4.0. CA3 z +1.08–1.13 and EC LII z +1.41 in all (p 0.0005).

Gate: W 1.6, 2.4 and 3.2 pass 1–3; W 4.0 fails 2 (EC LV 0.43 active). **Smallest passing W = 1.6.**
Prediction: wrong in the good direction (passes from 1.6, not 2.4).

Result: **with a stronger EC LII → EC LV input, EC LV locks to ripples and carries the memory**
(decoder 1.00 from W 1.6; at default it is at chance). From W 2.4 the memory also reaches mPFC
(decoder 0.83 p 0.001 at 2.4; 0.92 counts p 0.0005 at 3.2), but mPFC then fires in 43–69% of
cells per ripple. Caution: this is transfer, not learning. The EC LV identity can come straight
from the EC LII drive. One seed only.
Next (gate fixed above): W 1.6 on seed 303, and learning vs twin on both seeds. W 2.4 is the
smallest value that reaches mPFC, so it is worth the same test.

## 26. Does cortex learn, or only relay? Learning vs twin with the EC LV fix (2026-11-20)

Config: §25 sweep (`p3TP` flags + `--eclii-lv-k 60`), W = `--w-eclii-lv` 1.6 and 2.4, seeds 202
and 303. Learning `lvW_sS` (s202 = `lv16`, `lv24` from §25); twin `lvNW_sS` = the same plus
`--no-stc-hook --no-mpfc-assoc`. The real test of consolidation is recall after the lesion
(cortex without the hippocampus), so the primary readout is G2 here, against the twin.
Gate (fixed before the twin runs), per W:
1. **Primary: cortex learned.** G2 specificity learning > twin on both seeds, and learning G2
   p < 0.01 on both seeds.
2. CA1 → EC LII own−other Δw p < 0.01 on both seeds (learning runs).
3. Descriptive: EC LV / mPFC sleep decoder, learning vs twin.
Prediction: 2 passes; 1 fails (§20: G2 misses traces below 1 mV at 1%; §21–22: G2 equal in
twins); 3 equal in learning and twin (identity comes from the drive).

**Result (2026-11-20).** No `--g2-fixed-cue` in `rw.base`, so the G2 trial-label p is valid here.

| W | seed | G2 spec learning (p) | G2 spec twin (p) | CA1→EC own−other Δw (p) | mPFC active in SWR L / twin |
|---|---|---|---|---|---|
| 1.6 | 202 | +0.014 (0.029) | −0.010 (1.00) | +2.68 µV (0.0005) | — |
| 1.6 | 303 | +0.013 (0.032) | +0.003 (0.23) | +2.22 µV (0.0005) | — |
| 2.4 | 202 | **+0.018 (0.0055)** | +0.002 (0.34) | +2.39 µV (0.0005) | 0.43 / 0.34 |
| 2.4 | 303 | **+0.036 (0.0005)** | −0.001 (1.00) | +2.68 µV (0.0005) | 0.39 / 0.35 |

1. Primary: **PASS at W 2.4** (learning > twin and p < 0.01 on both seeds). FAIL at W 1.6
   (learning > twin on both seeds, but p 0.03). The prediction "1 fails" was wrong at W 2.4.
2. Δw: PASS on all 4 learning runs (still about 2.5 µV; the §24 size target of 4 µV is not met).
3. Sleep decoder: EC LV counts 1.00 in learning and twin alike (identity comes from the drive,
   as predicted). mPFC decoder is mixed and not higher in learning (s202 W2.4: L 0.83/0.50,
   twin 0.75/0.83). So the sleep code is relayed; only the post-lesion recall differs.

Caveats, not yet tested:
- The twin turns off two things: the STC hook (CA1→EC LII) and mPFC association learning.
  The G2 effect can come from either. CA1→EC Δw is only about 2.5 µV, so mPFC association
  learning is the more likely carrier. Next control: STC-only-off and mPFC-assoc-only-off
  twins at W 2.4, both seeds.
- mPFC is 39–43% active per ripple at W 2.4 (twin 34–35%). Learning raises mPFC activity,
  so part of the G2 gain may be gain, not specificity. G2 is an own−other contrast, so a pure
  gain change would not pass alone, but this is not checked.
- 1% only, 2 seeds, effect sizes small (+0.018, +0.036). Pilot until 12%.

## 27. Which rule carries post-lesion recall? Split twins at W 2.4 (2026-11-20)

The §26 twin turns off two rules at once. `--no-stc-hook` skips CA1→EC LII tag-and-capture.
`--no-mpfc-assoc` skips EC LV→mPFC association and the mPFC recurrent learning (same gate,
`replay_scaled.py` ~6212). Split twins, §26 W 2.4 config, seeds 202 and 303:
- `lvA24_sS` = `--no-stc-hook` only (mPFC learns, CA1→EC fixed).
- `lvB24_sS` = `--no-mpfc-assoc` only (CA1→EC learns, mPFC fixed).

Gate (fixed before the runs). A rule "carries recall" if its run, with only that rule on,
gives G2 specificity > the full twin (§26) and G2 p < 0.01 on both seeds.
Prediction: A passes, B fails. Reason: CA1→EC Δw is only about 2.5 µV, and mPFC learning is
directly on the readout path. If A passes and B fails, the STC hook adds nothing to recall:
this is the §0 claim-1 test (blocking capture must remove consolidation) run in reverse, and
it fails claim 1 for this config.

**Result (2026-11-20).** G2 specificity (perm p), W 2.4:

| seed | full learning (§26) | A: mPFC only (`--no-stc-hook`) | B: STC only (`--no-mpfc-assoc`) | full twin (§26) |
|---|---|---|---|---|
| 202 | +0.018 (0.0055) | +0.013 (0.033) | +0.005 (0.060) | +0.002 (0.34) |
| 303 | +0.036 (0.0005) | −0.003 (0.86) | +0.006 (0.067) | −0.001 (1.00) |

- Gate: **neither rule carries recall alone.** A fails (p 0.03 / 0.86). B fails (p 0.06 / 0.07).
  Only the two rules together pass. The prediction (A passes, B fails) was wrong.
- B is above the twin on both seeds (+0.005/+0.006 vs +0.002/−0.001), but not at p < 0.01.
  CA1→EC Δw in B is +2.46/+2.39 µV (p 0.0005), the same as with mPFC learning on.
- A is not consistent across seeds (+0.013 vs −0.003).
- On s303 the full effect (+0.036) is larger than A + B (+0.003). This suggests the rules
  interact: mPFC learning needs the CA1→EC trace. One run per cell, so this is not shown.
- mPFC activity per ripple: A 0.39/0.37, B 0.34/0.34, full 0.43/0.39, twin 0.34/0.35.
  mPFC learning raises mPFC activity; the CA1→EC rule alone does not.
- Claim 1 (blocking capture removes consolidation) is **not falsified** here: turning off the
  STC hook (A) removes the passing recall on both seeds.

Limits: 1 run per cell, 2 seeds, small effects. The G2 noise across seeds is not known, so
"interaction" vs "noise" needs more seeds (for example 4 seeds × full/A/B/twin at W 2.4).

## 28. Interaction or noise? 2 more seeds of full / A / B / twin at W 2.4 (2026-11-20)

Same config as §26–27, seeds 404 and 505. Names: `lv24_sS` (full), `lvA24_sS`, `lvB24_sS`,
`lvN24_sS` (twin). With §26–27 this gives 4 seeds × 4 conditions.

Gate (fixed before the runs), on G2 specificity per seed:
1. Replication: full learning passes G2 (p < 0.01, > twin) on both new seeds.
2. Interaction: I = full − A − B + twin. Real if I > 0 on 4/4 seeds and the bootstrap 95% CI
   of mean I over the 4 seeds (10,000 resamples) lies above 0.
   (4/4 signs alone is p 0.06 one-sided; this is weak and is reported as weak.)
3. Descriptive: A and B each vs twin, sign count over 4 seeds.
Prediction: 1 passes on 1 of 2 new seeds; 2 fails (I > 0 on 3/4 seeds, CI includes 0).

**Result (2026-11-20, runs 17:00–18:16).** G2 specificity (perm p), W 2.4:

| seed | full | A: mPFC only | B: STC only | twin | I = full − A − B + twin | CA1→EC Δw full (p) |
|---|---|---|---|---|---|---|
| 202 | +0.018 (0.0055) | +0.013 (0.033) | +0.005 (0.060) | +0.002 (0.34) | +0.002 | +2.39 µV (0.0005) |
| 303 | +0.036 (0.0005) | −0.003 (0.86) | +0.006 (0.067) | −0.001 (1.00) | +0.032 | +2.68 µV (0.0005) |
| 404 | +0.010 (0.047) | +0.000 (1.00) | +0.001 (0.35) | +0.000 (1.00) | +0.009 | +2.39 µV (0.0005) |
| 505 | +0.053 (0.0005) | +0.017 (0.0070) | −0.004 (0.90) | +0.000 (1.00) | +0.040 | +0.55 µV (0.073) |

Mean I +0.021, bootstrap 95% CI [+0.006, +0.036] over 4 seeds.

Gate:
1. Replication: **1 of 2.** s505 PASS (p 0.0005); s404 FAIL (p 0.047, > twin). Prediction right.
2. Interaction: **PASS as written** (I > 0 on 4/4, CI above 0). Prediction wrong. Weak: 4 seeds,
   s202 I is only +0.002, and a bootstrap over 4 values is narrow by construction.
3. A vs twin: higher on 3/4 (passes alone on s505, p 0.007). B vs twin: higher on 2/4.

Over all 4 seeds: full learning passes G2 on 3/4 and is above its twin on 4/4. Twin passes 0/4.
A passes 1/4, B 0/4.

Against the §27 idea "mPFC learning needs the CA1→EC trace": on s505 the full G2 is the
largest (+0.053) but the CA1→EC Δw is not specific there (+0.55 µV, p 0.07). So the interaction
does not go through a memory-specific CA1→EC weight on that seed. Mechanism unknown. One
candidate, not checked: STC raises all CA1→EC weights (mean Δw > 0), so EC LII and then EC LV /
mPFC fire more during sleep, and mPFC Hebbian learning gets more co-firing events (§17: the
number of co-firing events is the limit).

Result: **sleep learning gives post-lesion recall on 3 of 4 seeds, and needs both rules.** This is
a 1% pilot with small effects. The cause of the interaction is open.

## 29. Why do the two rules work together? mPFC co-firing in sleep, full vs A (2026-11-20)

Candidate from §28: STC raises all CA1→EC weights (mean Δw > 0), so cortex fires more in sleep,
and mPFC Hebbian learning gets more co-firing events. No new runs: the §26–28 files, full (`lv24*`)
vs A (`lvA24*`, STC off, mPFC learns), seeds 202/303/404/505.
Measures (sleep only, 12 epochs, SWR windows): EC LII / EC LV / mPFC active fraction;
`mpfc_recurrent/n_coactive` summed over 24 events (co-active recurrent synapses, the hook's own
learning events); recurrent Δw (w_final − `epoch_weights/mpfc_rec_pre`) on synapses inside one
G2 assembly minus synapses between assemblies.
Prediction / gate (fixed before the count). The candidate holds only if all three hold, each
full > A on ≥ 3/4 seeds:
1. EC LV and mPFC active per SWR. If this fails, the candidate is rejected.
2. Summed recurrent `n_coactive`.
3. Within-minus-between assembly recurrent Δw.
Descriptive: per seed, (full − A) in item 2 vs (full − A) in G2 (4 points, no test).

**Result.** Full / A per seed (sleep SWR windows; Δw = recurrent mPFC, inside − between G2 assemblies):

| seed | EC LV active | mPFC active | recurrent `n_coactive` | rec Δw in − betw (mV) | G2 assembly size | G2 |
|---|---|---|---|---|---|---|
| 202 | 0.280 / 0.271 | 0.430 / 0.392 | 12428 / 10488 | +0.30 / +0.38 | 23 / 12 | +0.018 / +0.013 |
| 303 | 0.277 / 0.265 | 0.386 / 0.366 | 9500 / 8419 | +0.25 / +0.40 | 30 / 15 | +0.036 / −0.003 |
| 404 | 0.265 / 0.268 | 0.375 / 0.376 | 9192 / 9066 | +0.46 / +0.22 | 14 / 14 | +0.010 / +0.000 |
| 505 | 0.286 / 0.290 | 0.405 / 0.411 | 10866 / 11292 | +0.28 / +0.22 | 19 / 22 | +0.053 / +0.017 |

EC LII active 0.066–0.073 in all runs (full ≈ A).

Gate:
1. EC LV and mPFC active, full > A: **2/4 (FAIL).** Candidate **rejected.**
2. `n_coactive` full > A: 3/4 (404 by 1%).
3. Recurrent Δw in − betw full > A: 2/4.
Descriptive: s505 has the largest G2 gain (+0.036) with fewer co-active events in full than
in A. The s303 gain (+0.039) comes with +13% events. No link across the 4 seeds.

Result: **the interaction is not "more cortical activity → more Hebbian events".** Full and A
have the same sleep activity on 2 of 4 seeds. The learned recurrent mPFC weights inside the
assemblies are not larger in full. So the extra recall in full is not in these sleep measures.
Not checked, remaining candidates:
- After the lesion (`--lesion-eclv-mpfc`) CA1 → cortex and EC LV → mPFC are both cut, so only
  the recurrent mPFC weights and the choice of assemblies can carry recall. Recurrent Δw inside
  assemblies is not larger in full (item 3), so the choice of assemblies is the open candidate.
- G2 assembly size differs (23 vs 12, 30 vs 15 on 202/303). The assemblies are picked from the
  sleep activity, so this changes what G2 measures. The 4-seed data shows no link to G2.
- Noise: §28 item 2 is weak (4 seeds).

## 30. Is the §28 recall real? G2 sensitivity now, and a gain check (2026-11-20)

Config: §26–28 W 2.4 (`rw.base` + sk264 + `--stc-ltp-tag-only --prp-threshold 6 --eclii-lv-k 60`).
Code: commit `81bd38f`, run from a frozen worktree (`out/em/fz_run.sh`), so later code edits
cannot change these runs.

**A. Plant test (G2 sensitivity in this config).** §20 found G2 blind to 1.0 mV, but that was a
quieter cortex. Twin config (`--no-stc-hook --no-mpfc-assoc`) + `--plant-trace DW`, DW 0.3 and
1.0 mV, seeds 202/303 (`pt03_sS`, `pt10_sS`). DW 0 = the §26 twins. 0.3 mV is the size of the
learned inside-assembly recurrent Δw (§29: +0.22 to +0.46 mV).
Detected = G2 p < 0.01 on both seeds. Validity: DW 0 must not be detected (it is not: p 0.34 / 1.0).
Prediction: 1.0 detected; 0.3 detected on 1 of 2 seeds.
Use: if 0.3 is not detected, the §28 full-learning G2 cannot come from the learned weight size
alone (assembly choice or another path).

**B. Gain check.** At W 2.4, mPFC is 39–43% active per ripple. W 2.0, full and twin, seeds
202/303 (`lv20_sS`, `lvN20_sS`).
Gate: mPFC active in ripple ≤ 0.35 in full, and full G2 p < 0.01 and > twin on both seeds.
Prediction: mPFC ≈ 0.30–0.35; G2 passes on 1 of 2 seeds (the effect shrinks with less drive).

**Result (runs 19:51–21:10).**

A. Plant test (twin config + planted recurrent trace):

| DW | s202 G2 (p) [planted syn] | s303 G2 (p) [planted syn] |
|---|---|---|
| 0 (§26 twin) | +0.002 (0.34) | −0.001 (1.00) |
| 0.3 mV | **+0.019 (0.0015)** [169] | −0.002 (1.00) [273] |
| 1.0 mV | +0.018 (0.015) [68] | +0.004 (0.097) [228] |

Neither DW is detected on both seeds. Prediction wrong for 1.0 mV.
- G2 is now more sensitive than in §20 (there 1.0 mV gave nothing; here 0.3 passes on s202).
  But detection is unreliable: it depends on the seed, and is not monotonic in DW.
- Same seed and config, different planted synapse counts (169 vs 68; 273 vs 228). The plant
  happens after the assemblies are chosen, so the assemblies themselves differ between the two
  runs: 3-thread runs are not repeatable here (§18 item 6, §20 caveat). Run-to-run noise in
  G2 is therefore large.
- Use for §28: full learning makes an inside-assembly recurrent Δw of +0.22 to +0.46 mV (§29),
  the same size as these plants. A 3/4 pass rate for full learning is about what a planted
  trace of that size gives (1 of 2 here). So the §28 result fits "learned weights of the
  planted size", but G2 alone cannot separate it from noise with 4 seeds.

B. Gain check, W 2.0:

| seed | mPFC active in SWR full / twin | G2 full (p) | G2 twin (p) |
|---|---|---|---|
| 202 | 0.288 / 0.270 | **+0.027 (0.0015)** | −0.001 (1.00) |
| 303 | 0.325 / 0.290 | +0.008 (0.17) | +0.000 (1.00) |

Gate: mPFC ≤ 0.35 PASS; G2 on both seeds FAIL (1 of 2). Prediction right.
With less mPFC activity, full learning is still above its twin on both seeds and passes on
one. So the effect is not only a gain effect of a very active mPFC, but it is not robust either.

Result: **the §28 recall is real in direction (full > twin on 6/6 seed-configs so far) but G2
is a noisy test.** Each G2 run is a coin with a bias. More seeds per condition is the only way
to get a firm answer at 1%. Fixed assemblies (§31) remove one noise source.

## 31. Dose: does more sleep give more recall? (2026-11-20)

Config: §26 W 2.4 (frozen code `81bd38f`). `--n-swr` 6 and 24 (12 = §26), full and twin, seeds
202/303 (`d06_sS`, `d06N_sS`, `d24_sS`, `d24N_sS`). 3 patterns: 2 / 4 / 8 SWR per memory.
At 6 SWR a memory has 4 ripple events < PRP threshold 6, so selective cells cannot capture:
less sleep also means no L-LTP. This is part of the dose, not removed.
Gate (fixed before the runs):
1. Primary (weights): recurrent mPFC Δw, inside − between the run's own G2 assemblies, rises
   6 < 12 < 24 on both seeds.
2. Primary (recall): G2 full − twin rises 6 < 12 < 24 on both seeds.
Prediction: 1 passes; 2 fails (G2 noise, §30).

**Result.** Rec Δw = recurrent mPFC, inside − between the run's own G2 assemblies.

| seed | SWR | rec Δw in − betw (mV) | assembly size | G2 full (p) | G2 twin (p) | full − twin |
|---|---|---|---|---|---|---|
| 202 | 6 | +0.555 | 13 | +0.061 (0.0005) | −0.003 (1.0) | +0.064 |
| 202 | 12 | +0.304 | 23 | +0.018 (0.0055) | +0.002 (0.34) | +0.016 |
| 202 | 24 | +0.396 | 13 | −0.006 (1.0) | +0.010 (0.018) | −0.016 |
| 303 | 6 | +0.315 | 21 | +0.011 (0.0050) | +0.009 (0.016) | +0.002 |
| 303 | 12 | +0.245 | 30 | +0.036 (0.0005) | −0.001 (1.0) | +0.037 |
| 303 | 24 | +0.108 | 32 | +0.021 (0.0085) | +0.006 (0.036) | +0.015 |

Gate:
1. Weights rise 6 < 12 < 24: **FAIL** on both seeds (6 SWR is the largest on both).
2. G2 full − twin rises: **FAIL** on both seeds.
Prediction 1 was wrong; prediction 2 was right.

Result: **no dose effect.** More sleep does not give larger learned mPFC weights or better recall.
Caveats:
- The weight measure uses each run's own assemblies, which differ between runs (13–32 cells).
  So the weight column mixes learning with the choice of cells.
- s202 at 6 SWR has the best G2 of all runs (+0.061), with no L-LTP possible (4 events < PRP 6).
  So this recall does not need STC capture. It agrees with §33: mPFC learning alone is enough.

## 32. LLM: can the EC LII memory reach CA3 without the CA3 drive? Routing sweep (2026-11-20)

§21: in EC LII mode (`--pattern-source ec-lii`, the database memory is the only pattern input),
CA3 stays at chance even with the JOB H16 routing (`emr`: CA3 z +0.09 / +0.18). Upstream
RESULTS §32 got +0.42 with the same routing. Our base (`out/em/em.base` = `emr` without the
routing flags) differs from upstream mainly by `--ca3-drive-scale 0.35` (constant CA3 inputs
× 0.35, WORKLOG §14), 12 vs 14 blocks, and the cortex flags (downstream of CA3).
Arms (seed 202, 12 SWR, frozen code `81bd38f`); routing R = `--mf-group-frac 0.7 --ec-ca3-k 12
--ec-ca3-w 1.0 --ec-ca3-group-frac 0.7` unless stated:
- `rt1`: R + `--ca3-drive-scale 1.0` (upstream drive).
- `rt2`: `--mf-group-frac 1.0 --ec-ca3-k 12 --ec-ca3-w 1.0 --ec-ca3-group-frac 1.0` (drive 0.35).
- `rt3`: rt2 routing + `--ca3-drive-scale 1.0`.
- `rt4`: R with `--ec-ca3-k 40 --ec-ca3-w 2.0` (strong perforant path; not anatomical).
Reference: `emr_s202` (R, drive 0.35): CA3 z +0.09.
Readout: `decode_identity.py` CA3 SUP and CA1 home-group z and decoder; CA3 SUP active
fraction in SWR windows (`lv_act.py` style).
Gate: an arm passes if CA3 SUP home z ≥ +0.40 with p < 0.01. The best passing arm then gets
seed 303 and the full sleep test (§26 learning vs twin) in EC LII mode.
Prediction: rt1 ≈ +0.3 (drive scale is the cause); rt3 passes; rt4 highest.

**Result** (`decode_identity.py`, seed 202, block-label shuffle p):

| arm | CA3 SUP z (p) | CA1 z (p) | EC LV z (p) | EC LV decoder rate+timing (p) |
|---|---|---|---|---|
| `emr` (reference) | +0.09 (0.24) | +0.13 (0.20) | −0.03 (0.33) | 0.08 (0.79) |
| `rt1` drive 1.0 | +0.13 (0.025) | +0.13 (0.15) | +0.04 (0.022) | 0.25 (0.25) |
| `rt2` routing frac 1.0 | +0.27 (0.041) | +0.23 (0.026) | +0.10 (0.004) | 0.17 (0.60) |
| `rt3` rt2 + drive 1.0 | +0.11 (0.023) | +0.01 (0.39) | +0.04 (0.095) | 0.25 (0.39) |
| `rt4` strong EC→CA3 | **+0.69 (0.0005)** | +0.12 (0.15) | −0.03 (0.36) | 0.83 (0.0015) |

EC LII z +1.40 and decoder 1.00 in all arms (the memory input works). mPFC at chance in all arms.

Gate (CA3 z ≥ +0.40, p < 0.01): **only `rt4` passes.**
Prediction: rt1 ≈ +0.3 wrong (+0.13); rt3 passes wrong; rt4 highest right.

Result: **the drive scale is not the cause.** Upstream drive (rt1, rt3) does not help. Only a
strong perforant path (40 synapses × 2.0, not anatomical) puts the database memory into CA3.
CA1 still does not carry it (+0.12), so the CA3 → CA1 hop also loses it.
Replication `rt4_s303`: CA3 SUP z **+0.66 (p 0.0005)**, CA1 +0.14 (0.23), EC LV +0.05 (0.07),
mPFC −0.01 (0.28). **rt4 passes on both seeds.** CA1 loses the memory on both seeds.
Next: the full sleep test in EC LII mode (waits for the user: rt4 routing is not anatomical).

## 33. Same G2 cells in every condition, and random replay (2026-11-20)

Code `ad206be` (frozen worktree `../thl-run2`, `out/em/fz2_run.sh`). S0 with all new flags off:
`8631eb29…` (`s0_after6`, `s0_after7`). Config: §26 W 2.4. Runs one at a time, next to the
other 2-run queue (RAM 63% free, 2.6 GB per run).

**A. Fixed assemblies.** `--g2-assemblies-from` the seed's twin (`lvN24_s202.h5`, `lvN24_s303.h5`),
so full, A and B are cued on the same cells (chosen without learning). `fa24_sS`, `faA24_sS`,
`faB24_sS`, seeds 202/303.
Gate: full G2 p < 0.01 and > twin on both seeds. Descriptive: I = full − A − B + twin.
Prediction: full passes on 1 of 2 (run noise, §30).

**B. Random replay.** Full learning + `--random-replay`, seeds 202/303 (`rr24_sS`).
Same CA3 cell count and timing per SWR, random cells. Note: the EC LII memory drive
(hybrid mode) still gives each epoch its memory, and at W 2.4 that drive reaches EC LV (§25).
Gate: "replay is needed" if G2 p ≥ 0.05 on both seeds. Prediction: fails on ≥ 1 seed, i.e. recall
partly survives, carried by the EC LII drive, not by CA3 replay.

**Result.** G2 specificity (trial-shuffle p); rec Δw = recurrent mPFC, inside − between assemblies.

| seed | arm | G2 (p) | rec Δw in − betw (mV) |
|---|---|---|---|
| 202 | full `fa24` | +0.040 (0.0010) | +0.324 |
| 202 | A, STC off `faA24` | +0.035 (0.0010) | +0.280 |
| 202 | B, mPFC off `faB24` | +0.001 (0.42) | — |
| 202 | twin `lvN24` | +0.002 (0.34) | — |
| 202 | random replay `rr24` | +0.000 (1.0) | +0.369 (own assemblies, 7 cells) |
| 303 | full `fa24` | +0.004 (0.10) | +0.195 |
| 303 | A `faA24` | +0.005 (0.13) | +0.202 |
| 303 | B `faB24` | −0.001 (1.0) | — |
| 303 | twin `lvN24` | −0.001 (1.0) | — |
| 303 | random replay `rr24` | −0.002 (0.70) | +0.214 (own assemblies, 24 cells) |

Assemblies: 11 cells (s202), 21 cells (s303), the same in all fixed arms.
Interaction I = full − A − B + twin: +0.006 (s202), −0.001 (s303).

Gate:
- A. Full G2 p < 0.01 and > twin on both seeds: **FAIL** (passes on s202 only). Prediction right.
- B. "Replay is needed" (G2 p ≥ 0.05 on both seeds): **PASS.** Prediction wrong.

Result:
1. **With the same cells in every arm, the STC × mPFC interaction is gone** (I ≈ 0 on both seeds).
   On s202, A (mPFC learning only) gives the same recall as full. The §28 interaction most
   probably came from the choice of assemblies, not from learning on shared cells.
2. **mPFC learning is the rule that carries G2 recall.** B (STC only) is at twin level on both seeds.
3. **Random CA3 replay removes recall on both seeds**, although mPFC still learns (rec Δw
   +0.37 / +0.21 mV, the same size as full). So the order and identity of replay matter, not the
   amount of learning. The EC LII memory drive alone does not carry recall.
   Caveat: full itself passes on only 1 of 2 seeds here, so the random-replay result is strong
   on s202 and weak on s303.

## 34. A larger STC trace (2026-11-20)

Same code and config, full learning. `--stc-capture-factor 2.0 --stc-w-max-rel 3.0` (`cf20_sS`)
and `--stc-capture-factor 3.0 --stc-w-max-rel 4.5` (`cf30_sS`), seeds 202/303. Default 1.3 / 1.5.
Gate: 1. size: CA1→EC LII own−other Δw ≥ 4 µV (§24 target), p < 0.01, both seeds.
2. Descriptive: G2 vs §28 full (+0.018 / +0.036).
Prediction: 1 passes at 3.0; G2 unchanged (the lesion cuts CA1 → cortex, §29).

**Result.** CA1 → EC LII own − other Δw (`ec_weight_readout.py`, 2000 label permutations).

| seed | capture factor / w max | own − other Δw (µV) | p | L-LTP own / other | G2 (p) |
|---|---|---|---|---|---|
| 202 | 1.3 / 1.5 (§26) | +2.39 | 0.0005 | 0.039 / 0.029 | +0.018 (0.0055) |
| 202 | 2.0 / 3.0 | +7.09 | 0.0005 | 0.037 / 0.024 | −0.002 (0.66) |
| 202 | 3.0 / 4.5 | +12.10 | 0.0005 | 0.046 / 0.031 | +0.000 (1.0) |
| 303 | 1.3 / 1.5 (§26) | +2.68 | 0.0005 | 0.037 / 0.023 | +0.036 (0.0005) |
| 303 | 2.0 / 3.0 | +7.15 | 0.0005 | 0.043 / 0.030 | +0.008 (0.19) |
| 303 | 3.0 / 4.5 | +8.27 | 0.0005 | 0.048 / 0.038 | +0.037 (0.0005) |

Gate 1 (size ≥ 4 µV, p < 0.01, both seeds): **PASS at 2.0 and at 3.0.** Prediction right
(it passes at 3.0), and 2.0 is already enough.
Descriptive: G2 is lower than §28 full in 3 of 4 runs. G2 is noisy (§30), so this is not a
finding. A larger CA1 → EC trace does not improve post-lesion mPFC recall, as expected (the
lesion leaves only recurrent mPFC weights).

## 35. LLM: the anatomical route EC LII → DG → CA3 (2026-11-21)

Question: can the database memory reach CA3 through DG and the mossy fibres, without the strong
non-anatomical EC → CA3 path of `rt4` (§32)?

Diagnosis (no new runs, `emr`, `rt1–rt4`; scratch `dgid.py`). DG GC identity in SWR windows:
each GC gets the pattern of the nearest ring centre (the rule the mossy-fibre grouping uses),
z across patterns per block, block-label shuffle.
- DG GC: own z +1.34 to +1.39, 12/12 blocks, p 0.0005 in all 6 runs; 6% active; own pattern
  fires +19 to +25% over the mean. **DG carries the memory.**
- CA3 SUP: 73–75% active per SWR window (emr, rt4), 7 Hz. Mostly 3 non-specific Poisson drives.
- Mossy in-degree is 15 per CA3 SUP cell (`TARGET_INDEGREE`); rat ~46–50 (RESULTS.md table,
  Amaral et al. 1990; not checked in the source here). With 6% GC active, a CA3 cell gets ~1 mossy
  spike per window, so the DG code drowns in the background.
So the memory is lost on the hop DG → CA3.

New opt-in flag `--mf-k K` (commit `1451f85`): mossy in-degree onto CA3 SUP; DEEP scaled by the
same factor. Default 0 keeps 15 / 8.

Arms (seed 202, `em.base`, frozen `../thl-run` = `1451f85`). All keep the anatomical EC → CA3 of
`emr` (`--ec-ca3-k 12 --ec-ca3-w 1.0 --ec-ca3-group-frac 0.7`):
- `dg1`: `--mf-group-frac 1.0 --mf-k 46`.
- `dg2`: `--mf-group-frac 0.7 --mf-k 46` (only the in-degree changes vs emr).
- `dg3`: dg1 + `--ca3-drive-scale 0.2` (less non-specific CA3 drive; a stand-in for inputs the
  model now has explicitly).
S0 with `--mf-k` off, in the same batch.
Gate (same as §32): an arm passes if CA3 SUP home z ≥ +0.40 with p < 0.01. Validity: DG GC
active ≤ 10% and CA3 SUP not runaway (rate < 20 Hz). Report CA1 z.
If an arm passes: seed 303, then the CA3 → CA1 hop (CA1 is at chance even in rt4).
Prediction: dg1 passes (z ~ +0.5); dg2 below gate; dg3 highest; CA1 stays < +0.2 in all arms.

**Result** (seed 202). S0 `s0_after8` = `8631eb29…` (unchanged).

| arm | mossy K | CA3 SUP z (p) | CA1 z (p) | EC LV z (p) | CA3 SUP active / Hz | CA1 active / Hz | DG own z, active |
|---|---|---|---|---|---|---|---|
| `emr` (ref) | 15 | +0.09 (0.24) | +0.13 (0.20) | −0.03 (0.33) | 0.73 / 6.9 | 0.60 / 5.5 | +1.39, 6% |
| `dg1` | 46 | +0.32 (0.004) | −0.13 (0.87) | +0.08 (0.010) | 0.74 / 7.1 | 0.55 / 4.8 | +1.36, 6% |
| `dg2` | 46, frac 0.7 | +0.23 (0.030) | −0.18 (0.92) | +0.05 (0.014) | 0.74 / 7.1 | 0.56 / 5.1 | +1.34, 6% |
| `dg3` | 46 + drive 0.2 | **+0.44 (0.001)** | +0.25 (0.026) | +0.04 (0.029) | 0.45 / 3.9 | 0.37 / 3.2 | +1.27, 6% |

Validity: DG ≤ 10% active and CA3 < 20 Hz in all arms (pass). mPFC at chance in all arms.
Gate (CA3 z ≥ +0.40, p < 0.01): **only `dg3` passes.**
Prediction: dg1 passes wrong (+0.32); dg2 below gate right; dg3 highest right; CA1 < +0.2 wrong
for dg3 (+0.25, p 0.026, not significant).

Result: **the anatomical route DG → CA3 carries the memory into CA3 when two things hold:**
the biological mossy in-degree (46) and less non-specific CA3 drive. The in-degree alone lifts
CA3 from +0.09 to +0.32. Less background lifts it to +0.44, and CA1 starts to follow (+0.25).
Cost: CA3 and CA1 rates fall to 3.9 / 3.2 Hz. Replay quality was not checked at drive 0.2.
Note: the log's replay ρ (first ripple pair only) is weak in all arms, the `emr` reference included
(EC LII mode has no CA3 sequence drive), so it does not separate the arms.

Replication `dg3_s303`: CA3 SUP z **+0.37 (p 0.003)**, 9/12 blocks; CA1 +0.14 (0.21); EC LV +0.05
(0.033); mPFC −0.10 (0.69). DG +1.40, 6% active. CA3 0.40 active / 3.5 Hz, CA1 0.36 / 3.1 Hz.
**Gate on s303: FAIL** (z +0.37 < +0.40, although p < 0.01). So dg3 passes on 1 of 2 seeds.

Result: **the DG route carries the memory into CA3 on both seeds (p ≤ 0.003), but more weakly than
rt4 (+0.44 / +0.37 vs +0.69 / +0.66), and below the fixed z threshold on s303.** CA1 does not get
the memory reliably (+0.25 / +0.14). The CA3 → CA1 hop is the next loss point.

## 36. Strengthen DG → CA3 with anatomical levers (2026-11-21)

Base = `dg3` (§35): `em.base` + `--ec-ca3-k 12 --ec-ca3-w 1.0 --ec-ca3-group-frac 0.7
--mf-group-frac 1.0 --mf-k 46 --ca3-drive-scale 0.2`. CA3 z +0.44 / +0.37. Code `1451f85` (frozen
`../thl-run`). Seeds 202 and 303 for every arm. One lever per arm:
- `sA`: `--mf-k 50` (top of the rat range 46–50).
- `sB`: `--ca3-drive-scale 0.1` (half the non-specific CA3 drive again).
- `sC`: `--pp-residual 0.7` (base 0.9): less Poisson stand-in on DG, so EC carries a larger share of
  the granule-cell drive. Targets the small DG contrast (own pattern only +20–25%).
- `sD`: `--dg-ec-cluster-sigma 0.03` (base 0.05): tighter EC → DG topography.
Gate: an arm passes if CA3 SUP home z ≥ +0.40 with p < 0.01 on **both** seeds.
Validity (else the arm is void): DG GC active ≤ 10% per SWR block; CA3 SUP < 20 Hz;
CA1 PYR ≥ 2 Hz in SWR windows (the code notes CA1 collapse when CA3 falls near 2.8 Hz).
Report CA1 z and DG own z / rate contrast.
Prediction: sA ≈ base (+4 inputs is small); sB passes but CA1 near the 2 Hz limit; sC raises the
DG contrast and passes; sD changes little.

**Result.** CA3 SUP / CA1 home z (p), block-label shuffle; rates in SWR windows.

| arm | seed | CA3 z (p) | CA1 z (p) | CA3 / CA1 Hz | DG active, own z | valid | gate |
|---|---|---|---|---|---|---|---|
| `dg3` (base) | 202 | +0.44 (0.001) | +0.25 (0.026) | 3.9 / 3.2 | 6%, +1.27 | yes | |
| `dg3` (base) | 303 | +0.37 (0.003) | +0.14 (0.21) | 3.5 / 3.1 | 6%, +1.40 | yes | |
| `sA` mf-k 50 | 202 | +0.49 (0.002) | +0.33 (0.016) | 3.9 / 2.9 | 7%, +1.32 | yes | |
| `sA` | 303 | +0.36 (0.008) | +0.20 (0.077) | 3.6 / 2.8 | 6%, +1.34 | yes | FAIL |
| `sB` drive 0.1 | 202 | +0.53 (0.001) | +0.42 (0.005) | 1.6 / **1.8** | 6%, +1.28 | **no** | |
| `sB` | 303 | +0.42 (0.0035) | +0.60 (0.0005) | 1.3 / **1.5** | 7%, +1.38 | **no** | VOID |
| `sC` pp-residual 0.7 | 202 | +0.31 (0.015) | +0.28 (0.045) | 3.8 / 3.0 | 4%, +1.23 | yes | |
| `sC` | 303 | +0.30 (0.016) | +0.14 (0.27) | 3.5 / 3.6 | 4%, +1.38 | yes | FAIL |
| `sD` EC→DG σ 0.03 | 202 | +0.41 (0.001) | +0.21 (0.039) | 4.0 / 3.2 | 6%, +1.27 | yes | |
| `sD` | 303 | +0.51 (0.0005) | +0.14 (0.20) | 3.5 / 2.8 | 6%, +1.41 | yes | **PASS** |

Gate: **only `sD` passes** (both seeds, valid). `sB` passes the z gate but is void: CA1 < 2 Hz.
Prediction: sA ≈ base right; sB near the CA1 limit — it went below (void); sC passes wrong
(DG got sparser, 4%, and CA3 fell); sD changes little wrong (it passes).

Caveats:
- The sD margin is small: s202 +0.41 is not above dg3 s202 (+0.44). The gain is on s303 only
  (+0.37 → +0.51). With 3-thread run noise this may be noise.
- DG own z did not rise in any arm (+1.23 to +1.41). So no lever sharpened the DG code itself.
- Side finding, `sB`: with half the background drive CA1 gets the memory (+0.42 / +0.60,
  p ≤ 0.005) — the first CA1 pass in EC LII mode — but at 1.5–1.8 Hz, below the validity limit.
  So the non-specific CA3 drive is what hides the memory in CA3 and CA1.

Noise check (fixed before the runs): seed 404 for `sD` and `dg3`. sD counts as a real gain over
dg3 only if sD z ≥ +0.40 (p < 0.01) on s404 and sD > dg3 on 2 of 3 seeds.

Noise check, seed 404: `sD` CA3 +0.47 (p 0.0045), CA1 +0.11 (0.27), 3.6 / 2.8 Hz;
`dg3` CA3 +0.38 (p 0.009), CA1 +0.20 (0.077), 3.6 / 2.9 Hz.
sD z ≥ +0.40 on s404: yes. sD > dg3: 2 of 3 seeds (303, 404). **Noise check PASS.**

Result: **sD (EC→DG σ 0.03) is the anatomical route that carries the memory into CA3 on 3 of 3
seeds** (+0.41 / +0.51 / +0.47, p ≤ 0.0045). The gain over dg3 is small (mean +0.06). CA1 stays
at chance on all 3 seeds (+0.21 / +0.14 / +0.11). The CA3 → CA1 hop is now the loss point.
Config for the next step: `em.base` + `--ec-ca3-k 12 --ec-ca3-w 1.0 --ec-ca3-group-frac 0.7
--mf-group-frac 1.0 --mf-k 46 --ca3-drive-scale 0.2 --dg-ec-cluster-sigma 0.03`.

## 37. The CA3 → CA1 hop in EC LII mode (2026-11-21)

Base = `sD` (§36): CA3 z +0.41 / +0.51 / +0.47, CA1 +0.21 / +0.14 / +0.11. In SWR windows CA3 SUP
is 45% active, CA1 37%. Schaffer: K 500 per CA1 cell, `--schaffer-group-frac 0.7` (10 CA3 groups).
Hint from `sB` (§36): with less CA3 background, CA1 got the memory (+0.42 / +0.60) but fell to
1.5–1.8 Hz. Code `1451f85` (frozen `../thl-run`), no new code. Seeds 202 and 303. Arms:
- `c1`: `--schaffer-group-frac 1.0` (every Schaffer input from the home group).
- `c2`: `--schaffer-k 264 --schaffer-group-frac 1.0` (the §26 Schaffer config).
- `c3`: `--ca3-drive-scale 0.1 --schaffer-w-scale 1.5` (sB background; CA1 rate restored through the
  Schaffer path, the path that carries the signal).
- `c4`: `--ca3-drive-scale 0.15`.
Gate: an arm passes if CA1 PYR home z ≥ +0.40 with p < 0.01 on both seeds, and CA3 SUP keeps
z ≥ +0.40 with p < 0.01.
Validity (else void): CA1 PYR 2–20 Hz and CA3 SUP < 20 Hz in SWR windows; DG GC active ≤ 10%.
Prediction: c1 ~ +0.25 (fails); c2 ~ +0.30 (fails); c3 passes; c4 CA1 near 2 Hz.

**Result.** Rates are in SWR windows (300–420, 600–720 ms per block). DG GC z +1.27–1.41 (p 0.0005)
and 6–7% active in every arm. Seeds 202 / 303:

| arm | CA3 SUP z (p) | CA1 PYR z (p) | CA3 / CA1 Hz | verdict |
|---|---|---|---|---|
| `c1` | +0.37 (0.002) / +0.44 (0.001) | +0.21 (0.04) / +0.10 (0.30) | 4.0 / 3.4, 3.5 / 2.8 | fail |
| `c2` | +0.43 (0.001) / +0.50 (0.001) | +0.19 (0.10) / +0.32 (0.017) | 3.8 / 3.8, 3.4 / 2.9 | fail |
| `c3` | +0.85 (0.0005) / +0.64 (0.0005) | **+0.47 (0.001) / +0.75 (0.0005)** | 1.6 / 3.9, 1.3 / 3.9 | **pass** |
| `c4` | +0.47 (0.002) / +0.51 (0.002) | +0.13 (0.21) / +0.14 (0.21) | 2.6 / 2.4, 2.3 / 2.1 | fail |

- Prediction held on all four arms. Cleaner Schaffer wiring (c1, c2) does not help: CA1 noise comes
  from the CA3 background, not from foreign Schaffer inputs.
- `c3` passes on 2 seeds and is valid (CA1 3.9 Hz). The same change also raises CA3 (+0.85 / +0.64 vs
  sD +0.41 / +0.51).
- Caveats: CA3 SUP is only 1.3–1.6 Hz in SWR windows, low for a ripple. DG is 6–7% active, above the
  2–4% target. 1% only, 2 seeds, 3 threads: a pilot until a third seed and 12%.
- c3 config: `em.base` + `--ec-ca3-k 12 --ec-ca3-w 1.0 --ec-ca3-group-frac 0.7 --mf-group-frac 1.0
  --mf-k 46 --dg-ec-cluster-sigma 0.03 --ca3-drive-scale 0.1 --schaffer-w-scale 1.5`.

**Third seed (pre-registered before the run).** `c3` on seed 404, same code `1451f85` and config.
Same gate and validity rules as above. Reference on seed 404: `sD` CA3 +0.47, CA1 +0.11.
Prediction: CA1 z ≥ +0.40 (pass).
