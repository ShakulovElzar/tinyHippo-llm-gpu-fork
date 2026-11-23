# Overview: tinyHippo-llm-gpu fork, 2026-11-10 to 2026-11-23

Branch `llm-work` of `ShakulovElzar/tinyHippo-llm-gpu-fork`. Full detail and every run: [WORKLOG.md](WORKLOG.md)
(section numbers below are WORKLOG sections). All results are at 1% scale, NEST 3.10, Apple M4.

## 1. Status in short

- A memory from the Nous database now travels the full loop EC LII → DG → CA3 → CA1 → EC LV → mPFC
  on 4/4 seeds (config `m1`, §44). In the starting model, identity was lost before cortex (§7).
- With group wiring this is relay, not consolidation. With random cortical wiring, a covariance
  rule during sleep writes pattern-specific CA1 → EC LV weights on 3/4 seeds (§48). The effect of
  those weights on EC LV activity is not yet reliable, and it does not reach mPFC.
- Every new mechanism is an opt-in flag. The default model is unchanged: the 1-thread S0 digest
  `8631eb29…` is the same after every flag.

## 2. Timeline

| dates | phase | outcome | WORKLOG |
|---|---|---|---|
| 11-10 | setup: fork, venv, L0 tests (8/8), run viewer | local runs work | top, §1 |
| 11-11 | reproducibility: S0 digest, `simbackend.py` shim, code review fixes | S0 gate for every change | §2–§6 |
| 11-11 to 11-13 | does the pattern reach cortex? three blocking faults found and fixed | pattern reaches mPFC on 3 seeds | §7–§14 |
| 11-13 | LLM layer (`llm/`): store, recall threshold, slot bank, Claude agent; code split into steps | recall@1 0.61–0.64 at false recall 0.06–0.12 | §15 |
| 11-13 to 11-14 | capacity; controls without plasticity; G2 recall probe | identity in cortex came from wiring; G2 at 1% unreliable | §16–§20 |
| 11-18 | Nous database memories as EC LII spike input (step 3a–3c) | input works; alone it does not reach CA3 | §21 |
| 11-18 to 11-20 | sleep learning with random cortex wiring, post-lesion recall | weak G2 effect 3/4 seeds; probe unreliable | §22 |
| 11-20 to 11-22 | the database memory, hop by hop, anatomical routing | full loop passes on 4/4 seeds (`m1`) | §23, §39–§44 |
| 11-22 to 11-23 | consolidation: plasticity rules on CA1 → EC LV with random wiring | covariance rule: specific weights 3/4 seeds | §45–§48 |

## 3. Before and after

Home-group identity z (block-label shuffle; ≈ 0 = no identity). Before: Max's baseline flags,
CA3-driven pattern, 3 seeds (§7, §12). After: `m1`, the database memory as the only input, 4 seeds (§44).
The input mode differs, so the rows compare the state of the loop, not one changed variable.

| stage | start (11-11) | now (`m1`, mean [95% t]) |
|---|---|---|
| CA3 SUP | +0.76 to +1.01, but 20 Hz with 99.8% of cells always active | +0.84 [+0.71, +0.96], 1.7–2.1 Hz |
| CA1 PYR | +0.40 to +0.52; no SWR burst | +0.51 [+0.41, +0.61] |
| EC LII | −0.04 to +0.38 (no inhibition) | input layer: +1.37 to +1.41 with the database drive (§21) |
| EC LV | −0.09 to +0.12 (27% of cells fire with no input) | +0.46 [+0.35, +0.57] |
| mPFC | −0.06 to +0.05 | +0.44 [+0.32, +0.56] |

## 4. Recommended configurations

### 4.1 Fixes that made the loop carry a pattern (use in every config)

| problem | flag and value | effect | § |
|---|---|---|---|
| EC LII has no inhibition; the most excitable cells always fire | `--ec-lii-ff-inhib -0.25` | CA1 → EC LII step fixed on 3 seeds | §8, §9, §13 |
| EC LV fires without input (rheobase < 0) | `--ec-lv-ie-shift -1` (−2 in `m1`), `--ec-lv-ff-inhib -0.25` (0 in `m1`) | pattern reaches EC LV on 3 seeds | §10, §11 |
| CA3 in a constant 20 Hz drive state | `--ca3-drive-scale 0.35` (0.1 in `m1`) | CA3 ≈ 9 Hz at 0.35, ≈ 2 Hz at 0.1; downstream z rises | §12, §14 |
| EC LV → mPFC too weak | `--w-eclv-mpfc 6` | pattern reaches mPFC on 3 seeds | §14 |
| Hebbian cap cut strong synapses (bug) | `--hebb-keep-strong` | mPFC learning becomes pattern-specific | §18 |
| lesion left EC LV → mPFC on | `--lesion-eclv-mpfc` | clean post-lesion baseline | §18 |

### 4.2 Relay of a database memory through the full loop: `m1` (PASS, 4/4 seeds)

`out/em/em.base` + the flags below, 24 blocks. Code `b201d09` or later.

| lever | flags | why | § |
|---|---|---|---|
| EC → CA3 routing | `--ec-ca3-k 12 --ec-ca3-w 1.0 --ec-ca3-group-frac 0.7 --mf-group-frac 1.0` | carry the EC LII memory into CA3 | §23 A |
| mossy fibres at rat in-degree | `--mf-k 46` (model had 15; rat 46–50) | about 1 mossy spike per window at K 15 | §23 A |
| sharper DG input | `--dg-ec-cluster-sigma 0.03` | CA3 +0.41 / +0.51 / +0.47 | §23 A |
| CA3 → CA1 | `--ca3-drive-scale 0.1 --schaffer-w-scale 1.5` | less non-specific CA3 drive, stronger Schaffer | §23 B |
| CA1 → EC LV | `--w-ca1-lv 1.35 --w-eclii-lv 0 --ec-lv-ff-inhib 0 --ec-lv-ie-shift -2` | CA1 becomes the only EC LV source | §39–§43 |
| CA3 strength | `--w-mf-sup 3.75` (default 2.5) | CA3 gain +0.33 on 4/4 seeds | §44 |
| cortex wiring | `--cortex-group-frac 1.0` | carries identity by wiring: relay only | §44 |

Limits: seeds 202 / 303 were used to choose the route; `m1` is a test config (EC LII → EC LV cut).

### 4.3 Consolidation test: `L48` (primary 1 PASS, primary 2 FAIL)

`m1` + `--cortex-group-frac 0 --ca1-ec-group-frac 0` (random cortex wiring, so the wiring gives
no identity) + `--stc-ec-lv --stc-ltp-tag-only --prp-threshold 6 --stc-capture-factor 2.0 --lv-cov-eta 0.1`.
Control: the same with `--no-stc-hook --no-mpfc-assoc` (no plasticity).

| rule on CA1 → EC LV | synaptic specificity (p < 0.01) | functional, L − twin (mean [95% t]) | § |
|---|---|---|---|
| STC tag-and-capture | 0/4 (98% of synapses saturate at the cap) | +0.07 [−0.45, +0.59] | §45 |
| STC + per-cell capture limit 20% | 0/4 | −0.10 [−0.31, +0.11] | §46 |
| covariance, Δw = η·w₀·(x−⟨x⟩)(y−⟨y⟩), η 0.1 | **3/4** (z +7.6 / +2.0 / +5.2 / +3.7) | +0.13 [−0.26, +0.51] | §48 |

Recommendation: use the covariance rule (`--lv-cov-eta 0.1`) for further consolidation work.
STC as built is a correlation rule: most CA1 cells fire in every SWR, so it potentiates almost
every synapse (§47).

### 4.4 Earlier learned-route result (weak; not recommended as proof)

`out/em/rw.base` + `--schaffer-w-scale 0.5 --schaffer-k 264 --schaffer-group-frac 1.0
--stc-ltp-tag-only --prp-threshold 6 --eclii-lv-k 60 --w-eclii-lv 2.4`: post-lesion G2 recall
above the no-plasticity twin on 4/4 seeds, passes on 3/4, interaction +0.021 [+0.006, +0.036].
But a planted-trace test showed that G2 is unreliable at 1% (§20, old §30 in §22).

## 5. What did not work (do not repeat)

- Weaker CA1 → EC LII weights, or CA1 → EC grouping alone: no identity in EC LII (§8).
- No theta (`--no-theta`): no SWR burst (§12).
- mPFC recurrent learning for G2 at 1%: single-seed passes do not replicate (§17, §18).
- EC LII → CA3 at 1% without mossy-fibre routing: CA3 stays at chance (§21, §23 A).
- Removing EC LV → CA3 feedback to rescue seed 202: rejected (§42).
- Per-cell weight normalisation (`--stc-lv-norm`): built, not run; it only rescales a flat trace (§46).

## 6. LLM layer

| part | state | § |
|---|---|---|
| memory store + recall (`llm/`), stub tfidf backend | no-recall threshold 0.6: recall@1 0.64 / 0.61, false recall 0.12 / 0.06 (tune / test seeds) | §15 |
| Russian text | tokenizer bug fixed (matched only `[a-z0-9]`) | §15 |
| agent (Claude API, tools remember / recall / sleep) | cues with the user's own words; paraphrase recall needs embeddings | §15 |
| `SlotBank` | memory s = model pattern s; error when full; capacity at 1% ≈ 10 | §15, §16 |
| Nous database → model | `llm/nous_export.py` (read-only) + `--ec-memories FILE`: each fact drives its own EC LII band | §21 |
| read memories back from cortex (step 3c) | identity in EC LV / mPFC with `m1`; learned trace only at the weight level (§48) | §21, §44, §48 |

## 7. Limits

- Everything is 1%. Cells per memory are few (EC LV 600 cells, 30 CA1 inputs each); 12% is not run.
- 3-thread runs are not bit-identical; replication is across seeds (4 per condition).
- Scorers: `analysis/score_chain.py` (chain z and rates), `analysis/score_cons.py` (§45–§48 gates), `analysis/score_bias.py` (§47). Run from the repo root on the run HDF5 files; the run files themselves are not committed.

## 8. How to check a change

```bash
.venv/bin/python replay_scaled.py $(cat out/em/s0.flags) --out-hdf5 out/em/s0_check.h5
.venv/bin/python analysis/h5_digest.py out/s0_fix.h5 out/em/s0_check.h5
```

Same digest (`8631eb29…`) = the default model is unchanged.
