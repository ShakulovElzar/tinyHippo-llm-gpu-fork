"""
izh_calibrate.py
----------------
Standalone numpy stand-in for NEST's izhikevich neuron model, used to
pre-calibrate intrinsic parameter sets for the DG-CA3 extension BEFORE
spending MN5 time on it. This integrates the canonical Izhikevich (2003)
ODE system directly:

    dv/dt = 0.04 v^2 + 5v + 140 - u + I
    du/dt = a (b v - u)
    if v >= 30: v <- c, u <- u + d

Same units/convention already in use in bidirectional_replay.py's
pyr_params / basket_params / olm_params (dimensionless I, not pA/nS),
integrated with forward Euler at dt=0.1 ms to match nest.SetKernelStatus
resolution=0.1 used throughout tinyHippo.

This is a PRE-CHECK, not a replacement for the NEST-side calibration
(izh_calibrate_nest.py) -- NEST's internal solver may differ slightly in
its treatment of synaptic input timing. Numbers here should be confirmed
on MN5 before being written into build_dg_ca3_network().
"""
import numpy as np

DT = 0.1        # ms, matches nest resolution used elsewhere in tinyHippo
T_MS = 3000.0   # ms per trial
RNG = np.random.default_rng(7)


def simulate_izh(a, b, c, d, I_e, drive_rate_hz, weight, t_ms=T_MS, dt=DT, seed=None):
    """Single Izhikevich neuron driven by a Poisson spike train.
    Each incoming spike delivers an instantaneous current kick of `weight`
    for one integration step (matches the classic I += S*firings convention).
    Returns output firing rate (Hz).
    """
    rng = np.random.default_rng(seed)
    n_steps = int(t_ms / dt)
    v = -65.0
    u = b * v
    spike_prob_per_step = drive_rate_hz * (dt / 1000.0)
    n_out_spikes = 0
    for _ in range(n_steps):
        I = I_e
        if rng.random() < spike_prob_per_step:
            I += weight
        v += dt * (0.04 * v * v + 5 * v + 140 - u + I)
        u += dt * (a * (b * v - u))
        if v >= 30.0:
            v = c
            u += d
            n_out_spikes += 1
    return n_out_spikes / (t_ms / 1000.0)


def f_i_curve(params, rates, weight, n_trials=3):
    out = []
    for r in rates:
        vals = [simulate_izh(*params, drive_rate_hz=r, weight=weight, seed=int(r * 13 + trial))
                 for trial in range(n_trials)]
        out.append(np.mean(vals))
    return np.array(out)


def half_activation_rate(rates, response, target_frac=0.5):
    """Drive rate at which response first crosses target_frac * max(response).
    NOTE: range-dependent (max is taken over the swept window) -- kept for
    reference only. Use rheobase_rate() for a stable, range-independent
    threshold comparison between parameter sets.
    """
    rmax = response.max()
    if rmax <= 0:
        return np.nan
    thresh = target_frac * rmax
    idx = np.where(response >= thresh)[0]
    return rates[idx[0]] if len(idx) else np.nan


def rheobase_rate(rates, response, criterion_hz=2.0):
    """Drive rate at which output first sustains >= criterion_hz.
    Range-independent (does not reference the max of the swept window),
    so it is the correct metric for comparing threshold shifts across
    parameter sets.
    """
    idx = np.where(response >= criterion_hz)[0]
    return rates[idx[0]] if len(idx) else np.nan


# -----------------------------------------------------------------------
# FINAL locked parameters (found via iterative rheobase-rate search).
# These are written into nest_dg_ca3_fi_calibration.py for NEST-side
# confirmation, and eventually into build_dg_ca3_network() in Phase 6.2.
# -----------------------------------------------------------------------
FINAL_PARAMS = {
    # label                          : (a,    b,   c,     d,   I_e)
    "PPGC_HGC":  (0.02, 0.2, -65.0, 8.0,  0.0),   # RS, = existing pyr_params
    "DG_BASKET": (0.10, 0.2, -65.0, 2.0,  0.0),   # FS, = existing basket_params
    "MC_LOW":    (0.02, 0.2, -65.0, 8.0,  0.0),   # RS baseline
    "MC_HIGH":   (0.02, 0.2, -65.0, 8.0, -9.0),   # RS + tonic hyperpolarizing bias
}

if __name__ == "__main__":
    weight = 20.0
    rates = np.arange(0, 6200, 100)
    CRIT = 2.0

    print(f"{'population':14s} {'rheobase(Hz)':>14s} {'max(Hz)':>10s}")
    results = {}
    for label, params in FINAL_PARAMS.items():
        resp = f_i_curve(params, rates, weight, n_trials=6)
        r = rheobase_rate(rates, resp, CRIT)
        results[label] = (resp, r)
        print(f"{label:14s} {r:14.1f} {resp.max():10.1f}")

    r_low, r_high = results["MC_LOW"][1], results["MC_HIGH"][1]
    print(f"\nMC_HIGH / MC_LOW rheobase ratio = {r_high/r_low:.2f}x  "
          f"(target 5.0x, per Kassab & Alexandre 2018 theta_l=0.1/theta_h=0.5)")
