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
`tinyHippo`, not a quick flag.

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
failed at 12%). His comment expects CA3 ~7.5 Hz; full-loop runs show ~20 Hz. Asked him; not changed.

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

Open items:
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
(kr, 3/3 seeds); before the fix it worked against the pattern. What blocks G2 at 1%: 120 mPFC
cells, sparse recurrent input per cue, and a priming state that is often not silent before the
cue. Not fixed by learning rate or in-degree alone.

**5. Priming sweep (kr flags + `--g2-trials 12`, seed 303, `pr*_s303`).** `--cr-prime-rate`
120 (kr) / 90 / 60 / 30 Hz: pre-cue baseline 0.35–0.61 / 0.74–0.91 / 0.00–0.22 / 0.16–0.42;
G2 +0.017 / +0.001 / +0.014 / −0.014 (p ≥ 0.22). The baseline does not follow the priming.
Cause: the lesion zeroes only CA1 → cortex. EC LV keeps firing at 2.7 Hz (its own background,
section 10) and drives mPFC through the 6 mV EC LV → mPFC weights, so mPFC fires at ~1.9 Hz
before any cue. That firing carries no pattern and swamps a cue whose learned effect is
~0.5 mV per cell.

Result: **at 1%, G2 cannot be shown with these mechanisms.** The learned trace exists in the
weights (kr, 3/3 seeds), but the recall test cannot read it out: too few recurrent inputs per
cue at 120 mPFC cells, plus pattern-free EC LV drive after the lesion.

Open items:
- Report own−other recurrent weight as the consolidation readout next to G2.
- 12%: run `kr` flags (`--hebb-keep-strong --mpfc-rec-a 0.3 --mpfc-rec-wmax 4`); 12× more mPFC
  cells removes the 1.7-input limit.
- Decide whether the lesion should also silence EC LV → mPFC drive, or
  whether G2 should be scored against a per-trial pre-cue baseline.
