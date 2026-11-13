# Dendritic Convolution: Optimization Principles for Electronic Spiking Neural Networks

## 0. Scope and framing

This note extends the original *Dendritic convolution* draft into a structured
account of how the dendritic-tree processing observed in the Associative
Cortex (AC) and Hippocampal system (HS) can be read as a three-stage
information-reduction (convolution) pipeline, and it closes with a feasibility
assessment of implementing that pipeline in electronic — specifically
memristive/CMOS mixed-signal — spiking neural network (SNN) hardware, in the
context of the tinyHippo project's NEST-based CA3/CA1 model.

The word "convolution" is used here in its information-theoretic sense — a
progressive folding-down of a high-dimensional input space onto a
lower-dimensional decision variable — rather than in the discrete-signal-
processing sense (sliding kernel). Each of the three stages below performs
one such folding step, and each step is a candidate site for hardware
optimization because each step is where information is *deliberately
discarded*, i.e. where a cheaper circuit can, in principle, replace an
expensive one without loss relative to the biological baseline.

## 1. First-level convolution: the postsynaptic dendritic spike

Neurotransmitter release at an excitatory synapse depolarizes the local
postsynaptic membrane in proportion to the synaptic weight `W`. When that
local depolarization crosses a threshold, a dendritic spike (dSpike) is
triggered locally, independent of the soma.

This is a **thresholding, weight-to-boolean convolution**: a graded,
analogue quantity (`W` × presynaptic activity) is compressed to a single bit
(dSpike fired / not fired) at the site of the synapse, well before the
signal reaches the soma. Two consequences follow that matter for hardware
design:

1. The nonlinearity is *local and per-branch*, not global and per-neuron —
   each dendritic segment behaves as an independent thresholding unit with
   its own operating point, rather than the whole neuron collapsing to a
   single soma-level threshold.
2. Because the compression happens at the synapse, all downstream circuitry
   (junction, soma) only ever has to process binary dendritic-spike events,
   not analogue synaptic currents. This is the first and largest point of
   potential savings for an electronic implementation: replacing an
   analogue multiply-accumulate at every synapse with a local
   compare-to-threshold operation whose output is a single wire.

### 1.1 Neuromodulation of the synaptic weight

`W` in the description above should not be read as a fixed, purely
Hebbian-set parameter. In the biological system it is under continuous,
time-varying gain control by ascending neuromodulatory afferents, and this
gain control is a principal mechanism by which memory consolidation and
temporal (state- and salience-dependent) weight update are implemented on
top of, and largely independently of, spike-timing-dependent plasticity
(STDP) itself:

- **Dopamine (DA)** — acting largely through D1/D2-class receptors — gates
  the transition from early- to late-phase potentiation. In the
  synaptic-tagging-and-capture (STC) framework this project already uses
  for CA1→EC consolidation, DA is the most direct biological analogue of
  the plasticity-related-protein (PRP) capture signal: a synapse can be
  tagged by coincident pre/post activity, but whether that tag is
  *captured* into a stable weight change is conditioned on a
  DA-dependent permissive signal, closely mirroring the `PRP_threshold`
  gate in the existing consolidation model.
- **Serotonin (5-HT)** modulates the sign and threshold of plasticity at
  many hippocampal and cortical synapses, and interacts with network
  excitability/inhibition balance, effectively shifting where the stage-1
  threshold sits without touching `W` directly.
- **Noradrenaline (NA)**, released under arousal and novelty, transiently
  raises gain and lowers the effective threshold for potentiation,
  consistent with its role in prioritizing salient or unexpected input for
  consolidation — a time-locked, arousal-gated multiplier on the
  otherwise activity-only weight update.
- **Acetylcholine (ACh)** shifts the hippocampal circuit between
  encoding-favoring and consolidation/replay-favoring regimes (high ACh
  during active exploration suppresses recurrent/feedback transmission and
  favors afferent-driven encoding; low ACh during quiet wakefulness and
  slow-wave sleep favors the recurrent replay this project's SWR
  simulations model), and thereby indirectly gates *when* stage-1
  thresholding is allowed to translate into lasting weight change.
- **Oxytocin (Oxt)** modulates interneuron excitability and social/
  salience-tagged plasticity in hippocampal and related circuits, acting
  as a further context-dependent multiplier on effective synaptic gain
  for specific classes of input.

Functionally, each of these neuromodulators acts on a slower timescale
than the millisecond-scale dSpike threshold crossing itself, so the
correct way to model their effect at stage 1 is as a **multiplicative,
slowly-varying gain term on `W`** (or, equivalently, a slow shift of the
local threshold), rather than as an additional fast synaptic input. This
distinction matters for the network-level claim of §0: it means the
"convolution" performed by the dendritic spike is not applied to a static
weight but to a weight that itself carries a second, slower time constant
set by neuromodulatory tone — which is exactly the mechanism needed to
implement selective, state-dependent memory consolidation without
requiring every synapse to be re-evaluated by STDP timing alone.

**Optimization idea.** Implement each synapse as a two-terminal memristive
element whose conductance encodes `W`, feeding a local comparator (or a
sub-threshold CMOS integrate-and-fire node) shared by a small cluster of
synapses on the same dendritic segment. The memristor removes the need for a
digital weight register and a digital multiplier; the comparator removes the
need to route an analogue current any further than the segment boundary.
This converts an O(N) analogue fan-in problem into an O(N) local threshold
problem followed by an O(1) digital wire per segment — a substantial
reduction in wiring and in analogue-to-digital conversion (ADC) load, which
is typically the dominant area and power cost in mixed-signal neuromorphic
chips. Neuromodulation can be added to this circuit cheaply because it is
slow: rather than a per-synapse fast input, a small number of global or
regional bias lines (one per modeled neuromodulator, analogous to DA, 5-HT,
NA, ACh and Oxt) can modulate either the memristor's write-enable
threshold (gating whether a coincidence-driven SET/RESET pulse is allowed
to change the stored conductance — the direct hardware analogue of tag
capture) or the comparator's reference voltage (shifting the effective
stage-1 threshold). Both mechanisms reuse existing circuit elements and
add only a handful of shared analogue bias wires per dendritic region,
rather than new circuitry per synapse.

## 2. Second-level convolution: the dendritic junction as an OR-gated refractory generator

A dendritic junction — the point where several dendritic branches converge
onto a parent branch or the soma — responds to the *first* dSpike that
arrives while it is idle, and then blocks further spikes from sibling
branches for the duration of that first spike's refractory period.

The functionally important point, worth stating precisely because it
determines the circuit that implements it, is that the junction does not
need to identify *which* branch fired first. Its contract is: if the OR of
its input branches is asserted while the junction is idle, enter a
refractory state for a fixed duration `τ_rf` and emit exactly one output
event (the junction spike, jSpike) marking that transition. Which branch
happened to trigger it is discarded along with everything else the
junction does not pass on. This makes the junction, functionally, a
coincidence-OR feeding a leaky-integrate-and-fire node with a hard
refractory period — the same circuit primitive as a spiking neuron, just
with "OR of upstream dSpikes" in place of a weighted synaptic sum, and
reusable at every level of the dendritic hierarchy (and, with different
fan-in and thresholds, at the soma itself).

This is a **coincidence-detection, time-domain convolution**: among
several branches that convolved their own inputs to a boolean value in
stage 1, the junction convolves *those* booleans down to a single "an
event occurred here" bit, gated by a fixed dead-time. Two things follow:

1. The junction performs sparsification "for free," using only a dead-time
   after the first qualifying input rather than an explicit
   comparison-of-magnitudes circuit. This is cheaper than a conventional
   winner-take-all (WTA) network, which normally requires lateral
   inhibition wired across all competing units — and it is cheaper still
   than a WTA that also has to resolve *which* input won, since the
   junction described here never computes that.
2. Because no arrival-order decision is ever made, the junction carries no
   risk of an arbitration artifact (a digitally-induced tie-break bias, or
   an analog metastability event) of the kind that a true first-past-the-post
   arbiter would have to resolve. What is preserved through the gate is
   coarser than order — only "something happened, no earlier than the last
   jSpike plus `τ_rf`" — which is a deliberately weaker guarantee than the
   original framing implied, and should be read as a simplification of the
   biological picture rather than a loss relative to it: the sparsification
   and dead-time behavior are preserved, the (unused) information about
   which branch won is simply never computed.

**Optimization idea — digital/mixed-signal ASIC.** Realize the junction as
a wired-OR of the branch dSpike lines (open-drain pull-downs onto a shared
rail — no OR-gate tree, and fan-in scales without added logic depth) into
a two-state finite-state machine (IDLE / REFRACTORY) built from standard
cells: on the wired-OR asserting while IDLE, load a down-counter with
`τ_rf / t_tick`, emit one jSpike pulse, and transition to REFRACTORY;
decrement the counter each tick; re-enter IDLE at zero. Because the
junction never needs to know which input arrived first, the counter only
has to resolve `τ_rf` to within a tick — it does not need to resolve *when
within a tick* the triggering input arrived — so this FSM can run on a
clock far coarser than the analog signal it is gating (see §5). The one
place fast logic is still required is input capture: a brief wired-OR
pulse can occur at any phase relative to a slow FSM clock, so a small
asynchronous edge-catcher (an SR latch set by the OR line, cleared
synchronously once the FSM has sampled it — a standard clock-domain-crossing
pattern) must sit between the fast dSpike lines and the slow FSM to avoid
dropping a brief triggering event. This is a well-understood, foundry-
qualified digital design pattern, not a research risk.

**Optimization idea — memristive/analog.** The same behavior can be
realized directly in device physics using a *volatile* (diffusive or
threshold-switching) memristor — two-terminal devices, reported in the
neuromorphic-device literature in material systems such as Ag- or
Cu-filament threshold switches and NbOₓ-type Mott-insulator switches, that
transition to a low-resistance ON state once a current or voltage pulse
crosses a SET threshold and then spontaneously relax back to the
high-resistance OFF state over an intrinsic retention time, with no
separate timing capacitor or digital counter needed. Each branch's dSpike
delivers a current pulse to a shared node through a diode-OR-like element
(a threshold/maximum detector, not a precision summer, which relaxes the
linearity requirements on the analog front end considerably relative to a
true summing amplifier); the first pulse to cross the device's SET
threshold switches it ON, a downstream comparator sensing the ON state
emits the jSpike, and the device's own relaxation dynamics *are* the
refractory period, with the ON-state I–V characteristic making the device
insensitive to further input pulses while it recovers. This folds "OR +
threshold + refractory timer" into a single device rather than three
circuit blocks, which is attractive for area and power at the density a
biologically-faithful dendritic tree would require (potentially thousands
of junctions per neuron). It should be stated precisely, in keeping with
not overselling device readiness: reported relaxation/retention times for
volatile memristors span a wide range in the literature — roughly
microseconds to seconds — depending on material system, filament
geometry, and operating conditions, so reliably targeting a specific
`τ_rf` in the low-to-mid millisecond range is a device-engineering and
characterization problem, not something the technology class guarantees
by default. Cell-to-cell and cycle-to-cycle variability in that relaxation
time would need to be characterized and, if excessive, compensated (design
margining, or a hybrid device-plus-CMOS trim) before this could be relied
on as the sole source of `τ_rf` in a production design. A pragmatic
near-term path is therefore the CMOS FSM described above (foundry-standard,
low risk, immediately tapeable), with the volatile-memristor realization
treated as a higher-payoff, higher-risk path for a later design iteration
once device retention statistics for the target `τ_rf` are characterized.

### 2.1 Clustering of synapses

Synapses onto a given neuron are not distributed at random across the
dendritic tree; morphologically, inputs that originate from correlated or
functionally related sources terminate closer together on the tree. Two
functional consequences follow directly from stages 1 and 2 above:

- Co-clustered synapses share a dendritic segment and therefore share a
  stage-1 threshold and a stage-2 junction, so correlated sources are
  convolved together more effectively than uncorrelated ones — the
  morphology itself implements a similarity-based grouping prior, before
  any learning occurs.
- Channels judged more important (by whatever developmental or activity-
  dependent criterion the biological system applies) are allocated a larger
  number of parallel projections into AC/HS, i.e. importance is encoded as
  redundancy of wiring, not as a larger weight on a single wire.

**Optimization idea.** In a crossbar-based memristive implementation, this
maps onto *deliberate non-uniform crossbar topology*: rather than a fully
connected, uniform crossbar where every input reaches every neuron with
equal wire length and equal fan-out, correlated input channels should be
routed to physically adjacent rows/columns feeding a shared local
comparator group, and important channels should be given multiple physical
memristive rows rather than one row of larger conductance. This is a
routing/floorplanning optimization more than a device-level one, and it is
the stage most constrained by fabrication (interconnect layers, crossbar
tiling), discussed further in §4.

## 3. Third-level convolution: somatic integration

The soma integrates the surviving dendritic-junction outputs together with
direct inhibitory synaptic input, and collapses the entire tree's activity
to exactly two scalar influences: net excitatory drive and net inhibitory
drive, whose difference (or ratio, depending on the modeling convention)
determines whether and when the neuron fires.

This is the **final and most aggressive convolution** in the pipeline: an
arbitrarily large dendritic tree, already reduced at stages 1 and 2, is now
reduced to two numbers. The biological cost of this aggressiveness is real —
over-compression at the soma is a plausible route to a non-functional or
pathologically synchronized network — so the soma's operating point
represents an explicit compromise between compression efficiency and the
minimum information the network needs to remain functionally expressive.

**Optimization idea.** Electronically, this argues for a two-line summing
bus per neuron (one excitatory accumulation node, one inhibitory
accumulation node) rather than per-synapse digital readout, with the
final excitatory/inhibitory comparison performed by a single differential
integrate-and-fire circuit. This is already close to how most neuromorphic
silicon neurons are built (Loihi, BrainScaleS, TrueNorth-style cores);
the contribution of the dendritic-convolution framing is to justify, from a
biological first-principles argument, *why* the two-line reduction is not
merely a hardware simplification but a computationally load-bearing
feature of the original system — which in turn argues against adding
additional somatic input channels (e.g. neuromodulatory third and fourth
lines) purely for hardware convenience without checking whether they change
network-level dynamics.

### 3.1 A concrete reference topology

![Reference circuit topology for the 
dendritic-convolution pipeline: per-synapse 
threshold units feed a two-level hierarchy of 
OR-gated refractory junctions (each level with 
its own 5–10 ms τ_rf), converging on a soma that also receives a direct, dendritic-bypass inhibitory input, followed by a fixed-delay axon stage.](https://raw.githubusercontent.com/max-talanov/tinyHippo/refs/heads/main/dendritic_convolution.png)

**Figure 1.** Reference circuit topology for a two-cluster excitatory
dendritic tree feeding a single soma, instantiating the three-stage
convolution pipeline of §§1–3 as a concrete block diagram. Per-synapse
threshold units (`thr`, stage 1, §1) convert each excitatory synapse's
weighted input to a boolean dSpike. Two clusters of excitatory synapses
(`Cluster1`, `Cluster2` — the morphological grouping discussed in §2.1)
feed a first tier of OR-gated refractory junctions (`junction th/rp`,
stage 2, §2), each carrying its own 5–10 ms `τ_rf`; their outputs
converge on a second-tier junction, itself carrying an independent 5–10 ms
`τ_rf`, before reaching the soma. A third cluster of inhibitory synapses
(`Cluster3`) bypasses the threshold/junction pipeline entirely and drives
the soma directly, and the soma output propagates through a final,
fixed-delay axon stage before leaving the neuron.

This diagram makes several points from earlier sections concrete rather
than schematic, and is worth reading alongside them directly:

- **The junction hierarchy is literally two independent instances of the
  same `τ_rf`-gated primitive**, exactly the "reusable leaf cell"
  construction argued for in §2 and §4.2 — the figure's `junction th/rp`
  block appears twice (once per hierarchy level) with identical internal
  structure and independently tunable `τ_rf`, rather than as two
  different circuit designs. The `Soma th/rp` block carries the same
  tag, which is the diagram's way of showing that the soma is that same
  threshold-plus-refractory primitive again, just with different fan-in
  and (presumably) a different threshold and `τ_rf` — the point made
  when discussing ASIC reuse for this pipeline.
- **Stacking two hierarchy levels stacks their dead-times.** Because each
  level's junction has its own independent 5–10 ms `τ_rf` and the second
  level only starts its own refractory window once it receives a jSpike
  from the first, the worst-case synapse-to-soma latency contributed by
  the junction hierarchy alone is on the order of two `τ_rf` periods
  (roughly 10–20 ms for 5–10 ms per level), not one. This is a concrete,
  diagram-derived number that sharpens §5.6's tick-sizing discussion: a
  deeper hierarchy multiplies the network-level dead-time budget
  linearly with depth, which is a real cost of adding hierarchy levels
  for biological fidelity (§4.2) and should be weighed against it.
- **Inhibition bypasses the dendritic pipeline entirely.** The figure
  makes explicit an architectural claim that §3's text left implicit:
  `Cluster3`'s inhibitory synapses connect directly to the soma, with no
  `thr` or `junction` stage in between. This is consistent with the
  perisomatic/proximal targeting of many fast inhibitory inputs in the
  biological hippocampus and cortex (e.g., basket-cell-type inhibition
  acting close to the soma rather than on distal dendrites), and it
  matters electronically: the inhibitory line needs none of the
  stage-1/stage-2 circuitry discussed in §§1–2 and §4.1–4.2, only a
  direct connection into the somatic summing node of §3's "two-line
  summing bus," which is a further, diagram-confirmed simplification of
  the inhibitory path relative to the excitatory one.
- **The axon delay is a separate, decoupled stage.** The final `axon
  delay` block is drawn outside the soma and outside the `τ_rf`-scale
  circuitry entirely — it is a fixed propagation delay applied after the
  somatic decision has already been made. This lines up with §5.5's
  recommendation that network-level routing/propagation logic can stay
  clocked digital without weakening the timing claims made about stages
  1–2: the diagram physically separates the millisecond-scale dendritic
  front end from this simple, decoupled delay element.

## 4. Feasibility analysis of an electronic dendritic-convolution SNN

The following assesses, stage by stage, how far current (as of this
writing) electronic device and circuit technology can realize the pipeline
above, and where the open problems are.

### 4.1 Stage 1 (synapse + local threshold): high feasibility

Two-terminal memristive devices (RRAM/HfOx, PCM, and related resistive
switching technologies) that store an analogue or multi-level conductance
and are read out by a local CMOS comparator or leaky-integrate-and-fire
node are a mature research area with working silicon demonstrations at
kilo- to mega-synapse scale. This stage is the closest to off-the-shelf:
crossbar arrays with per-row or per-column threshold circuits are routinely
fabricated in academic and some commercial neuromorphic prototypes. The
main open engineering issues are device-level, not architectural:

- **Conductance drift and cycle-to-cycle variability** in RRAM/PCM devices
  (typically single-digit to tens-of-percent variation depending on
  technology and write scheme) directly perturbs the effective dendritic
  threshold, which — because stage 1 is a hard threshold, not a graded
  readout — can flip a "spike"/"no spike" decision near the boundary. This
  is more consequential here than in a conventional analogue
  multiply-accumulate crossbar, where small conductance errors merely
  perturb a continuous sum. Threshold circuits sitting on top of memristive
  weights therefore need either wider design margins or periodic
  recalibration, both of which cost area or energy.
- **Endurance** (write-cycle lifetime) matters only insofar as the design
  intends on-chip learning (weight updates via SET/RESET pulses); a
  fixed-weight, inference-only realization of stage 1 is not endurance-
  limited.

Verdict: feasible today at prototype scale (hundreds to low thousands of
synapses per die); production-scale reliability engineering (drift
compensation, per-cell calibration) is incremental, not fundamental,
research.

### 4.2 Stage 2 (junction / OR-gated refractory generator): high feasibility

The OR-plus-refractory-FSM implementation proposed in §2 is circuit-trivial
in digital CMOS (a wired-OR, an edge-catcher latch, and a two-state
down-counter FSM is a handful of standard cells) and, because the junction
never has to resolve *which* input arrived first, there is no arbitration
or metastability-management circuitry to design or verify — this raises
the feasibility of this stage relative to a true first-past-the-post
arbiter. The open questions are architectural/parametric rather than
device-level:

- **Fan-in topology.** Biological dendritic trees have a branching junction
  structure (many small local junctions feeding progressively fewer, larger
  junctions toward the soma). Replicating a multi-level junction hierarchy
  in silicon means routing binary dSpike wires through several logic levels
  per neuron rather than a single flat OR gate, which multiplies the
  per-neuron logic footprint roughly linearly with the number of hierarchy
  levels chosen. A shallow (one- or two-level) approximation is cheap; a
  biologically faithful multi-level tree is a larger but still bounded
  digital design problem, well within reach of a standard-cell ASIC flow —
  and because each level is the same reusable OR-plus-refractory leaf cell
  (§2), adding levels is a replication cost, not a new design.
- **Refractory window matching.** The refractory period must be tuned
  relative to the expected inter-spike arrival rate of competing branches;
  too short a window fails to suppress legitimate closely-spaced arrivals
  from the same event, too long a window under-utilizes the junction's
  temporal bandwidth and, at high input rates, risks folding together
  events that a downstream consumer (e.g., a replay-order metric) would
  need distinguished. This is a parameter-tuning problem addressable by
  simulation (e.g., against the tinyHippo NEST model's own inter-group
  timing, which in the SWR replay experiments already documented in
  `bidirectional_replay.py` runs on a millisecond scale — ~3.8 ms between
  sequence groups at 10% network scale), not an open research question.
- **Volatile-memristor realization specifically.** If `τ_rf` is implemented
  as a memristor's intrinsic relaxation time rather than a digital counter
  (§2), device retention variability becomes the dominant risk, per §4.1's
  discussion of conductance drift — here affecting a *timing* parameter
  rather than a stored weight, which is a less-studied failure mode and
  should be treated as the higher-risk of the two implementation options
  in §2 until characterized.

Verdict: feasible with a straightforward digital design (the CMOS FSM
option in §2), and this is now the more clearly "solved" of the two
custom-circuit stages precisely because it does not need to arbitrate
order; the volatile-memristor option is feasible in principle but carries
device-characterization risk specific to hitting a target `τ_rf`, similar
in kind to (though distinct in mechanism from) the conductance-drift risk
already flagged for stage 1.

### 4.3 Clustering / topology-aware routing: the binding constraint

This is the stage most likely to determine whether the overall architecture
is practical at scale. A crossbar array is, by construction, a uniform,
fully connected fabric: every row reaches every column with comparable wire
length. Deliberately clustering correlated inputs onto shared local
segments, and giving important channels redundant physical rows, works
against that uniformity and requires either:

- non-uniform, application-specific floorplanning at design time (feasible
  for a fixed, known input structure such as a specific hippocampal
  circuit model, but not reconfigurable after fabrication), or
- a reconfigurable interconnect fabric (programmable switch matrix between
  crossbar tiles) that can be set up post-fabrication to approximate
  whatever clustering the trained/biological model calls for, at the cost
  of extra silicon area and extra parasitic capacitance on every
  reconfigurable link.

Both are demonstrated techniques individually (application-specific
neuromorphic ASICs use the former; FPGA-style programmable interconnect is
the latter), but combining fine-grained, dendrite-level clustering with a
dense memristive synapse array is closer to a monolithic 3D integration
problem (multiple tiers of memristive crossbars and CMOS logic stacked and
connected by dense through-silicon vias) than to a 2D chip layout problem.
Monolithic 3D memristive/CMOS stacks exist as research demonstrations but
are not yet a mature, foundry-available process the way 2D RRAM crossbars
are.

Verdict: feasible in principle, but this is the stage where the proposal
goes from "engineering" to "applied research." A 2D approximation
(coarse, design-time clustering fixed at fabrication) is achievable now; a
fully general, dendrite-faithful clustering fabric is a 3–5 year hardware
research horizon at the time of writing, contingent on continued progress
in 3D memristive integration.

### 4.4 Stage 3 (somatic two-line summation): high feasibility

This is architecturally the least novel part of the proposal — differential
excitatory/inhibitory integrate-and-fire somas are already standard in
existing neuromorphic silicon (Loihi/Loihi 2, BrainScaleS, TrueNorth-class
designs). The contribution of this framing is conceptual (justifying the
two-line reduction from a biological information-budget argument) rather
than requiring new circuitry.

Verdict: fully feasible with existing, deployed circuit techniques.

### 4.5 System-level assessment

| Stage | Core electronic primitive | Feasibility | Dominant risk |
|---|---|---|---|
| Postsynaptic dSpike | Memristor + local comparator | High (prototype-ready) | Conductance drift shifting the threshold |
| Junction / OR-refractory generator | Wired-OR + edge-catcher + counter FSM (or volatile memristor) | High | Hierarchy depth (digital) / `τ_rf` retention variability (memristive) |
| Synaptic clustering | Non-uniform crossbar floorplan / reconfigurable interconnect | Moderate | Requires 3D or application-specific fabric to be biologically faithful |
| Somatic E/I summation | Differential integrate-and-fire | High (already standard) | None specific to this proposal |

The net argument for building this pipeline in hardware, rather than a
conventional flat SNN core, is a *wiring and conversion* argument: stages 1
and 2 convert what would otherwise be a large analogue fan-in per neuron
into a small number of digital dSpike wires before any ADC is needed, which
is where a conventional dense crossbar chip spends most of its area and
power budget. The clustering stage is what actually captures the wiring
savings implied by that reduction, which is precisely why it is also the
hardest stage to realize faithfully — the benefit and the difficulty are
the same feature. A pragmatic path for the tinyHippo project is therefore
to validate stages 1–2 first (they map directly onto operations the
existing NEST model already performs numerically — thresholded dendritic
nonlinearity and a timing-gated update analogous to the tag-and-capture STC
mechanism already used for CA1→EC consolidation), and to treat stage-2.1
clustering as a design-time, application-specific floorplan rather than a
general reconfigurable fabric until 3D memristive integration matures
further. This keeps the electronic implementation question tractable while
still testing the network-level hypothesis — that dendrite-level
convolution reduces the information reaching the soma without collapsing
the network into non-functional over-simplification — that motivates the
whole proposal.

## 5. Continuous time as the gap between a pure digital solution and the proposed approach

Every implementation choice discussed in §§1–4 is compatible, in principle,
with a purely synchronous digital realization: quantize time into fixed
ticks, represent `W` as a multi-bit register, evaluate the stage-1
threshold once per tick, resolve the stage-2 junction with a clocked
priority encoder, and accumulate stage-3 sums in a digital adder. This is,
in fact, how most existing digital neuromorphic silicon (Loihi/Loihi 2,
TrueNorth-class cores) and the tinyHippo NEST simulation itself already
operate — NEST's default solver advances the network in fixed simulation
steps (commonly sub-millisecond, e.g. 0.1 ms) and evaluates neuron and
synapse dynamics at those steps rather than continuously. It is worth
being explicit about what is lost by that choice, because it is precisely
the gap that a continuous-time, event-driven analog or mixed-signal
realization of the dendritic-convolution pipeline is proposed to close.

### 5.1 What "continuous time" means for each stage

- **Stage 1 (threshold crossing).** The dendritic spike is triggered at
  the instant the membrane potential crosses threshold, a continuous,
  real-valued event time. A clocked digital evaluator only observes the
  membrane state at tick boundaries, so the reported crossing time is
  quantized to the tick period `Δt` and carries an expected timing error
  of up to `Δt`/2. Sub-threshold CMOS or translinear analog circuits
  (the classical Mead-style neuromorphic approach) instead implement the
  membrane state as a genuinely continuous voltage or current governed by
  an RC-like differential equation, and the comparator fires
  asynchronously, exactly when threshold is crossed, with a hardware
  latency set by transistor bandwidth (typically nanoseconds to low
  microseconds) rather than by a simulation tick.
- **Stage 2 (junction OR-detection).** With the junction specified as in
  §2 — OR the inputs, and if asserted while idle, block for `τ_rf` and
  emit one jSpike — there is no arrival-order decision to make, and
  therefore no arbitration-artifact risk of the kind an earlier draft of
  this section attributed to this stage. What remains genuinely
  timing-sensitive is narrower: (a) not missing a brief OR-assertion that
  falls between two ticks of a slow digital clock, which is solved by the
  asynchronous edge-catcher described in §2, not by clocking the whole
  junction faster; and (b) sizing `τ_rf` correctly relative to the
  clock, which §5.6 works through quantitatively. Continuous time still
  matters here, but for input capture, not for resolving competition.
- **Stage 3 (somatic integration).** The excitatory/inhibitory balance is
  integrated over a leak time constant that is itself continuous; how
  finely a digital implementation must sample it depends on how fast that
  time constant is relative to `Δt`. This stage is the least sensitive of
  the three, because summation is a linear, low-pass operation that
  tolerates modest time-quantization without qualitative error — consistent
  with §4.4's assessment that stage 3 is already adequately served by
  existing digital/mixed-signal somatic circuits.

### 5.2 Quantifying the gap against the tinyHippo timing regime

The bidirectional-replay simulations already in this project provide a
concrete scale against which to size the required timing precision.
Sequence groups activate roughly 3.8 ms apart during an SWR at 10% network
scale, and the STDP window used for tagging is ±20 ms with a forward axonal
delay of about 3 ms. Two implications follow directly:

1. A digital tick coarser than roughly a few hundred microseconds begins
   to risk folding two closely-spaced sequence-group-driven dSpikes into
   the same junction tick, which — given the corrected junction spec of
   §2 — does not corrupt an arrival-order decision (there is none to
   corrupt) but can still cost network-level replay-order fidelity if the
   tick is coarse enough to merge dSpikes from *different* sequence
   groups into the *same* jSpike or the same refractory window; a tick on
   the order of the 3.8 ms inter-group spacing (or coarser, as is typical
   of default 0.1–1 ms digital-SNN and NEST time steps once several tick
   periods of latency are added by synchronous pipeline stages) is
   adequate for network-level replay-order statistics (the Spearman-ρ
   metric already used to score replay quality) but is not adequate for
   preserving fine-grained relative timing *within* a single SWR event at
   the resolution the biological circuit appears to use. §5.6 works out
   the specific bound this places on the junction's own tick size.
2. The forward/reverse LTP/LTD asymmetry in the STC mechanism depends on
   the sign of a millisecond-scale timing difference (+3 ms vs. −3 ms).
   Any digital implementation whose effective tick or pipeline latency
   approaches that few-millisecond scale risks collapsing the sign
   distinction that separates consolidating from de-potentiating synapses
   — turning a designed asymmetry into noise.

In short: the network-level, statistical claims this project already
validates in simulation (replay quality, consolidation curves) are
tick-tolerant at typical digital-SNN/NEST time steps; the synapse- and
dendrite-level timing claims that motivate the dendritic-convolution
proposal in §§1–3 are not, and are the specific place where a purely
digital, clocked implementation departs furthest from the biological (and
simulated) target.

### 5.3 Cost side of the gap: why "just use a finer clock" is not free

Shrinking `Δt` to close the timing gap does not come for free in a
synchronous digital design: doubling clock frequency to halve `Δt`
roughly doubles dynamic switching power (power scales approximately
linearly with clock frequency in CMOS, all else equal) and requires every
neuron and synapse in the array to be re-evaluated on every tick whether
or not it has anything to do — an `O(N)` per-tick cost regardless of how
sparse the actual spiking activity is. This is the well-known
event-driven-vs-clocked trade-off in neuromorphic engineering: a clocked
digital design pays a fixed per-tick tax on the entire array to buy
timing resolution, while an asynchronous, continuous-time analog design
pays energy only when a threshold is actually crossed (current flows in a
comparator only around a transition) and its timing resolution is set by
device physics rather than by a clock budget. For a sparse hippocampal
replay-style workload — a small fraction of neurons active per SWR
event — this favors continuous-time, event-driven circuits on energy
grounds as well as on timing-fidelity grounds, which reinforces rather
than competes with the wiring-reduction argument made in §4.5.

### 5.4 What continuous time costs in return

The gap does not close for free on the analog side either, and it is
important to state the reciprocal cost precisely rather than treat
continuous-time analog circuits as a strictly dominant option:

- **No natural notion of a global "simulation state."** A clocked digital
  design can be paused, checkpointed, and stepped deterministically —
  useful for debugging and for reproducing the exact `bidirectional_replay.py`-
  style trace-by-trace comparisons this project already relies on.
  Continuous-time analog circuits are intrinsically real-time and
  free-running; extracting a reproducible, inspectable trace requires
  additional instrumentation (fast ADCs on monitored nodes) that
  reintroduces some of the sampling/quantization question the analog
  approach was meant to avoid, just moved to the measurement layer.
- **Device-level noise and drift are continuous too.** The same
  continuous physics that gives an analog comparator its sub-microsecond
  timing precision also lets thermal noise, flicker noise, and
  memristor conductance drift (§4.1) act continuously on the threshold,
  so timing precision in the abstract does not automatically translate
  into timing *accuracy* without calibration.
- **Verification and yield.** With the corrected junction spec of §2 this
  point no longer applies to stage 2's core function (there is no
  arrival-order arbiter to characterize near coincidence), but it
  resurfaces for the volatile-memristor realization of `τ_rf`: a digital
  counter's dead-time is fully specified and reproducible across chips,
  while a device-physics relaxation time carries cycle-to-cycle and
  cell-to-cell variability that must be characterized before it can be
  trusted as a production timing reference (§2, §4.2). The general
  point — that moving a function into continuous-time device physics
  trades deterministic, easily verified digital behavior for a
  distribution that must be measured and margined — still holds; it is
  just not, in this corrected version of the proposal, a metastability
  problem specifically.

### 5.5 Recommended position

Given §§5.1–5.4, the pragmatic reading is that continuous time is not an
all-or-nothing architectural choice but a resource that should be spent
where the biological claim actually needs it. Stages 1 and 2 — where the
proposal's own argument rests on exact threshold-crossing time and
arrival order — are where a continuous-time, asynchronous analog or
mixed-signal front end earns its cost. Stage 3, and all network-level,
routing-layer logic (spike packet transport between neurons, the digital
bookkeeping already well served by existing crossbar/router architectures
in Loihi-class chips), can remain clocked digital without materially
weakening the timing claims of §§1–3, because summation over a leak time
constant is the one stage in this pipeline that is genuinely tolerant of
tick-scale quantization. This mixed strategy — continuous-time analog (or a fast asynchronous
edge-catcher) at the synapse/dendrite boundary, clocked digital everywhere
else — is also the strategy already implicit in the feasibility ranking of
§4.5, and with the corrected junction spec of §2 the case for stage 2
specifically is now narrower than the original draft of this section
suggested: stage 2's continuous-time requirement is confined to not
missing a brief OR-assertion between ticks, not to resolving arrival
order, which is a materially smaller and cheaper ask.

### 5.6 How coarse can the junction's own tick be, given `τ_rf`?

A natural question, given that the junction's refractory period `τ_rf` is
itself commonly cited in the 5–10 ms range for dendritic spikes, is
whether the junction's own digital logic could simply run at a tick near
`τ_rf` — i.e., 1–10 ms — rather than at the sub-millisecond scale implied
by §5.2. The corrected junction spec of §2 makes the answer more favorable
than it would be for a true arbiter, but the two timescales involved
should not be conflated:

- `τ_rf` bounds how often the junction can report a **new** event: since
  the junction is blocked for `τ_rf` after firing, its maximum output
  rate is `1/τ_rf` (roughly 100–200 Hz for `τ_rf` = 5–10 ms). Downstream
  logic — propagating the jSpike, updating the somatic accumulator,
  network-level bookkeeping — genuinely does not need to sample this
  channel faster than `τ_rf` to avoid losing decisions, and a synchronous
  FSM tick approaching `τ_rf` is defensible for that purpose alone. This
  is the sense in which the intuition behind a 1–10 ms system tick is
  correct, and it is *more* clearly correct here than it would be for a
  true first-past-the-post arbiter, precisely because the junction no
  longer needs to preserve order information that a coarse tick could
  corrupt.
- `τ_rf` does **not** by itself bound how finely the *input capture* stage
  needs to resolve the OR-assertion. Two candidate dSpikes converging on
  one junction can be much closer together than `τ_rf` — in the tinyHippo
  timing regime, consecutive sequence-group activations are only ~3.8 ms
  apart, well inside a 5–10 ms refractory window — so multiple jSpike-
  triggering events from *distinct* upstream sources can cluster inside a
  single junction dead-time. Because the junction only needs to know
  *that* the OR fired, not *which* input did, this no longer creates an
  arbitration problem; but if the goal is also to preserve which
  higher-level sequence group produced which jSpike (a network-level,
  not junction-level, requirement — relevant to the Spearman-ρ
  replay-order metric), the tick governing *when the OR is sampled* still
  needs to be commensurate with the ~3.8 ms inter-event spacing, not with
  `τ_rf`.
- There is also a phase-alignment issue independent of both numbers above:
  a synchronous tick set equal to `τ_rf` only avoids missing events if it
  happens to be aligned to the start of each refractory window, which an
  asynchronously-arriving biological input never guarantees. Without the
  edge-catcher described in §2 (or oversampling by roughly 2–10×), a tick
  at `τ_rf` can miss or mis-time a brief OR-assertion that straddles a
  tick boundary.

Net assessment: your intuition is correct for the **junction's own
bookkeeping and downstream propagation logic** — a 1–10 ms tick, and
specifically the low end of that range given the ~3.8 ms inter-event
spacing already present in the tinyHippo model, is an adequate and
inexpensive design point, and the corrected OR-plus-refractory spec makes
it *more* defensible than it would have been under the original
winner-take-all framing, since no ordering fidelity is being traded away
by using a coarse tick. It does not, however, extend to the fast
edge-capture element sitting between the analog dSpike lines and that
slow tick domain — that element still needs to operate on a timescale set
by the shortest gap between competing inputs (sub-millisecond in this
project's own SWR timing), not by `τ_rf`, precisely so that the coarse
downstream tick has a correct, un-aliased OR signal to sample in the
first place. This also substantially weakens the energy argument in §5.3
as applied specifically to stage 2: at a 1–10 ms tick, clock power is not
a binding constraint (kHz-range clocking is trivially cheap in CMOS), so
the case for continuous-time circuitry at the junction rests entirely on
correct edge capture, not on energy savings from avoiding a faster clock.

## 6. Network-level topology: the same argument one level up

Figure 1 (§3.1) worked out the pipeline inside a single neuron. The
argument extends directly to the network that connects many such neurons
together, and it is worth showing that extension explicitly rather than
leaving it implicit.

![Network-level topology: three input channels 
of varying population size converge through a millisecond-scale slow spike router into a Hippocampal System (HS) population, which diverges through a second slow spike router into three associative-cortex target populations of matching sizes; every neuron in every population is tagged th/rp/del, the same threshold/refractory-period/delay primitive used inside a single neuron's pipeline.](https://raw.githubusercontent.com/max-talanov/tinyHippo/refs/heads/main/network_level_routing_topology.jpeg)

**Figure 2.** Network-level instantiation of the same architecture:
three input channels (`input ch 1/2/3`, populations of 6, 3, and 2
neurons respectively) converge through a **slow spike router (ms)** onto
a central `HS` (Hippocampal System) population, which diverges through a
second **slow spike router (ms)** onto three associative-cortex target
populations (`assoc. 1/2/3`) of matching sizes. Every neuron in every
population — input, HS, and associative — carries the same `th/rp/del`
tag.

Three points from earlier sections generalize directly from this figure:

- **The reusable leaf cell now spans the whole neuron, not just one
  stage.** Figure 1 showed `thr`, `junction th/rp`, and `Soma th/rp` as
  three separate instances of a shared threshold-plus-refractory
  primitive inside one neuron's dendritic pipeline. Figure 2 shows that,
  once assembled, that whole pipeline — threshold, refractory period,
  *and* the axon delay from §3.1 — collapses to a single `neuron th/rp/del`
  tile that is replicated without modification across every population in
  the network, from small two-neuron populations (`assoc. 3`) to
  six-neuron ones (`input ch 1`, `assoc. 1`). This is the network-level
  payoff of the ASIC leaf-cell argument made in §2 and §4.2: the same
  standard cell that composes a single neuron also composes the network,
  which is what makes a design of this kind tractable to verify and
  characterize at scale rather than as a collection of bespoke circuits.
- **The router is where the "network-level routing-layer logic" of §5.5
  physically lives, and it is explicitly labeled at the timescale §5.6
  argued for.** §5.5 recommended that spike-packet transport between
  neurons "can remain clocked digital... because summation over a leak
  time constant is the one stage in this pipeline that is genuinely
  tolerant of tick-scale quantization," and §5.6 derived that the
  junction's own bookkeeping tick can reasonably sit in the low-to-mid
  millisecond range given this project's ~3.8 ms inter-event spacing.
  Figure 2 draws that conclusion as an explicit, separate circuit block —
  the **slow spike router (ms)** — visually and functionally distinct
  from the `neuron th/rp/del` tiles it connects, with its millisecond
  timescale stated directly on the block rather than left as an inferred
  design parameter. This is a useful confirmation that the router
  abstraction the earlier timing analysis argued for is also the natural
  unit boundary at the network level: fast, dendrite-scale computation
  stays inside the neuron tile, and everything that needs to be
  compatible with a coarse tick — packet transport between populations —
  is factored into its own block.
- **The converge/diverge symmetry mirrors the project's own
  hippocampo-cortical loop.** Three variously-sized input channels funnel
  through one router into a single HS population, which then fans back
  out through a second router into three variously-sized associative
  target populations of matching sizes (6/3/2 in, 6/3/2 out). This
  convergent-then-divergent topology — many cortical input channels
  compressed through a hippocampal bottleneck and then re-expanded back
  out to cortex — is structurally the same shape as the CA3/CA1/EC loop
  already modeled in this project's NEST simulations (`bidirectional_replay.py`,
  `mem_cons_plan.md`): multiple upstream input channels converging on a
  smaller associative core, and a divergent return path carrying the
  consolidated result back out to multiple cortical targets. The figure
  should be read as a schematic of that same converge-diverge shape at
  the level of input/HS/associative-cortex populations, not as a claim
  that `input ch 1/2/3` and `assoc. 1/2/3` map one-to-one onto specific
  named subfields (e.g. CA3, CA1, individual EC layers) — that finer
  correspondence, if wanted, is a separate modeling decision for the
  tinyHippo circuit rather than something this diagram asserts on its
  own.