# tinyHippo

A bio-plausible spiking model of the rat hippocampus in [NEST](https://nest-simulator.readthedocs.io)
(Izhikevich neurons), built to study **memory consolidation through bidirectional
replay and sharp-wave ripples** across the full entorhinal–hippocampal loop:

```
EC LII → DG → CA3 → CA1 → EC LII/LV → mPFC
   ↑                              │
   └──────────────────────────────┘
```

The model scales from a 1% test network (~8k neurons, runs on a laptop) to the
full rat hippocampus (~780k neurons, MareNostrum 5), with the same code path.

A companion document,
[`hippocampal_timescales_as_circuit_spec.md`](docs/hardware/hippocampal_timescales_as_circuit_spec.md),
takes this model's validated timescales and mechanisms (synaptic tagging and
capture, replay-driven consolidation) and specifies them as a memristor-based
neuromorphic circuit — organic volatile devices for the hippocampal tag,
inorganic non-volatile crossbars for the cortical store, with replay as the
handoff between them.

## What the model does

| Capability | Flag | Status |
|---|---|---|
| **Bidirectional replay** — forward & reverse sequence replay during SWRs | *(default)* | validated at 12% (ρ_fwd +0.70, ρ_rev −0.54) |
| **CA3 recurrent feedback loops** — Watson 2025 four-way asymmetric wiring + E↔I | *(always on)* | core |
| **DG pattern separation** — granule sparse coding via basket feedback | `--dg` | validated at 12% (2.2% active/pattern) |
| **CA3 pattern completion** — auto-association, partial cue → full pattern | `--pattern-completion` | validated at 12% (sharp ~30% threshold, ablation-controlled) |
| **Synaptic tagging & capture** — early-LTP → tag → PRP → late-LTP on CA1→EC | `--stc` | implemented |
| **Memory consolidation** — hippocampo-cortical loop (EC LII, EC LV, mPFC) | `--ec-lii --ec-lv --mpfc` | implemented |
| **Synaptic homeostasis** — sleep downscaling, cortical L-LTP exempt | `--homeostasis` | implemented |
| **Topographic DG wiring** — clustered EC LII→GC fan-in, restores pattern identity washed out by uniform random sampling | `--dg-ec-cluster-sigma` | validated at 1% and 12% (small, real effect) |
| **Pattern discrimination probes** — per-population Jaccard identity/timing separation across interleaved patterns | `--n-patterns` | implemented |

An interactive map of all capabilities, with the functions implementing each,
is in [`capability_map.html`](docs/capability_map.html) (open it in a browser).

## Quick start

Install NEST ≥ 3.9 (see [INSTALL.md](docs/setup/INSTALL.md)), then:

```bash
# 1% test network: replay + dentate gyrus, ~1 min on a laptop
python replay_scaled.py --scale 1 --dg --dg-scale 2 --no-figures

# CA3 pattern completion probe (intact vs ablated recurrence)
python replay_scaled.py --scale 1 --pattern-completion

# full consolidation stack
python replay_scaled.py --scale 1 --dg --ec-lii --stc --n-swr 3
```

Results are written to a self-describing HDF5 file (all populations, spike
times, rates, and per-capability metrics), so analysis and plotting run
anywhere without NEST.

## LLM episodic memory (this fork)

An LLM agent stores and recalls facts through the model: `remember(text)` puts the
text in SQLite and gives the memory a slot (one CA3 pattern group per memory),
`sleep` runs replay and consolidation, `recall(cue)` cues the model and decodes which
slot comes back. The model holds the index, not the text.

```bash
export ANTHROPIC_API_KEY=...                       # needed for the agent only
python -m llm.agent --backend tfidf --db out/agent_memory.sqlite
python -m llm.bench.run_bench --backend tfidf --sweep   # retrieval benchmark, no LLM
python -m pytest -q tests
```

The model backend is not wired in yet; `tfidf` and `keyword` are stand-ins with the
same interface. Plans: [docs/plans/plan_branch_llm_integration.md](docs/plans/plan_branch_llm_integration.md),
progress: [docs/results/WORKLOG.md](docs/results/WORKLOG.md).

## Running on HPC

[`hpc/run.sh`](hpc/run.sh) is the SLURM launcher (MareNostrum 5, MPI + OpenMP). Submit from the repo root:

```bash
# replay + DG at 12%
sbatch --export=ALL,SCALE=12,DG=1,NO_STC=1,EC_LII=0,EC_LV=0,MPFC=0 hpc/run.sh

# pattern completion at 12%
sbatch --export=ALL,SCALE=12,PATTERN_COMPLETION=1 hpc/run.sh

# full stack with DG + consolidation
sbatch --export=ALL,SCALE=12,DG=1,N_SWR=14 hpc/run.sh
```

Single-neuron f-I calibration has its own job:
`sbatch --export=ALL,PROBE=dc hpc/run_calibrate.sh` → [`run_calibrate.sh`](hpc/run_calibrate.sh).

## Layout

```
replay_scaled.py     the model: every population, capability and the HDF5 export
tiny.py              theta / SWR generators and seeding
simbackend.py        thin layer over NEST, so NEST GPU can be swapped in by a flag

llm/                 LLM episodic memory: SQLite store, backends, slot bank, Claude agent
tests/               pytest suite for llm/
viewer/              local web viewer for runs: spikes and wiring
analysis/            decode_identity.py (pattern-ID readout), h5_digest.py (bit-identity
                     check), reconstruct_connectivity.py (rebuild a run's wiring)
plots/               figures from a run's HDF5 (replay_plot.py, consolidation,
                     pattern completion, architecture, activity profiles, paper figure)
calibration/         single-neuron Izhikevich f-I calibration (numpy and NEST)
hpc/                 SLURM launchers for MareNostrum 5; submit from the repo root
legacy/              early bidirectional-replay prototypes, kept for reference
docs/
  setup/             INSTALL.md, COMPATIBILITY.md
  plans/             HANDOFF.md, LLM / GPU / plasticity plans, phase plan
  results/           RESULTS.md (upstream log), RESULTS_llm_gpu.md, WORKLOG.md (this fork)
  hardware/          memristive circuit spec, dendritic convolution notes
  capability_map.html
figures/             images used by the docs
```

Run every script from the repo root, e.g. `python analysis/decode_identity.py out/run.h5`.
Local run output goes to `out/` (not committed).

## Results

**Memory consolidation is dissociable from replay.** Blocking late-LTP capture
(`--prp-threshold 999`) leaves replay quality identical (Δρ_fwd = 0.000) while
cortical consolidation goes to zero — separating the replay mechanism from the
consolidation mechanism in the same model. Full circuit, 12% scale:

![consolidation vs replay](/figures/final_comparison_fig9.png)

**CA3 performs pattern completion.** A partial cue of a stored assembly is
restored to the full pattern by the recurrent collaterals, with a sharp
attractor threshold near 30% cue. Ablating the within-group recurrence
(`sup_local = 0`) abolishes it, confirming the collaterals — not the cue — do
the work:

![pattern completion](/figures/pattern_completion.png)

**Sparsifying the cortex makes consolidation selective — but not yet
specific.** A cortical sparsity retune (§11 in [RESULTS.md](docs/results/RESULTS.md)) turns
saturated, all-cell L-LTP into a differentiated trace (7.2% of EC cells
consolidate, weight CV 0.17). Scored against standard engram criteria
(Josselyn & Tonegawa 2020), that trace is sparse and persistent but not yet
**specific**: no cortical population discriminates pattern A from pattern B
(§13), and hippocampal lesion does not impair cortical recall at the 12%
scale tested (§12, Test 3 negative). Two convergent, non-topographic
projections are implicated — DG's perforant path and, more severely, CA3→CA1
Schaffer collaterals at 100% density — and a topographic fix
(`--dg-ec-cluster-sigma`) moves DG's identity signal off zero for the first
time, though the effect is still small (§17–18). Full scorecard and
in-progress work: [RESULTS.md](docs/results/RESULTS.md).

## Key references

- Watson et al. (2025) *Cell Reports* 44:116080 — cell-specific CA3 wiring
  (superficial/deep split)
- Marr (1971); Nakazawa et al. (2002) — CA3 auto-association / pattern completion
- Frey & Morris (1997) — synaptic tagging and capture
- Kassab & Alexandre (2018) — DG mossy-cell threshold classes
- Andersen et al. (2007) *The Hippocampus Book* — reference neuron counts
- Josselyn & Tonegawa (2020) *Science* 367:eaaw4325 — engram criteria (sparse,
  persistent, specific, sufficient, necessary)
- Dolorfo & Amaral (1998) — entorhinal-dentate medial-lateral topography,
  motivating the clustered perforant-path fan-in
- Izhikevich (2006) — polychronization / delay-based temporal coding
- Caus, Sławek, Mazur, Zawal, Baś, Szaciłowski, Talanov & Abdi (2026) — memristive
  hippocampus hypothesis; candidate tag-element devices for
  [`hippocampal_timescales_as_circuit_spec.md`](docs/hardware/hippocampal_timescales_as_circuit_spec.md)
