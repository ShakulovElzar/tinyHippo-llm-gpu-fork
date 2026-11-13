#!/bin/bash -l
#SBATCH --job-name=DG_CA3_FI_CALIB
#SBATCH --output=dg_ca3_fi_calib_%A_%a.slurmout
#SBATCH --error=dg_ca3_fi_calib_%A_%a.slurmerr
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:20:00
#SBATCH --partition=gp_bsccs

# Phase 6.1 f-I calibration (default params)
#   sbatch hpc/run_calibrate.sh

# Even finer threshold resolution (10 Hz steps, more repeats -> tighter rheobase)
#   sbatch --export=ALL,N_REPEATS=16,FINE_RATE_STEP=10 hpc/run_calibrate.sh

# Re-tuning MC_HIGH's I_e: sweep the threshold region only, cheaply
#   sbatch --export=ALL,RATE_MAX=1200,FINE_RATE_MAX=1200,FINE_RATE_STEP=10 hpc/run_calibrate.sh

# DC rheobase only -- this is the measurement that tests the 5.0x MC target.
# Much cheaper than the Poisson sweep (no synapses, deterministic).
#   sbatch --export=ALL,PROBE=dc hpc/run_calibrate.sh

# Finer DC resolution
#   sbatch --export=ALL,PROBE=dc,DC_STEP=0.01 hpc/run_calibrate.sh

# Data-only run, no PNG (e.g. for a batch of calibration variants)
#   sbatch --export=ALL,NO_FIGURES=1 hpc/run_calibrate.sh

SIM_MS=${SIM_MS:-3000}
N_REPEATS=${N_REPEATS:-8}
RATE_MAX=${RATE_MAX:-6200}
RATE_STEP=${RATE_STEP:-200}
# Fine grid over the threshold region. The 2026-07-22 run used a uniform
# 200 Hz step with a 2 Hz criterion, which floored every population's
# rheobase at the first swept rate and produced a spurious 1.00x
# MC_HIGH/MC_LOW ratio. See the script docstring.
FINE_RATE_MAX=${FINE_RATE_MAX:-800}
FINE_RATE_STEP=${FINE_RATE_STEP:-20}
WEIGHT=${WEIGHT:-20.0}
CRITERION_HZ=${CRITERION_HZ:-2.0}
# DC current probe. This is the authoritative rheobase measurement -- the
# Poisson probe cannot measure rheobase at WEIGHT=20.0, because a single EPSP
# (+20 mV) already spans MC_LOW's entire rest-to-threshold gap (20.00 mV).
PROBE=${PROBE:-both}
DC_MAX=${DC_MAX:-30.0}
DC_STEP=${DC_STEP:-0.05}
DC_SIM_MS=${DC_SIM_MS:-3000}
DC_SETTLE_MS=${DC_SETTLE_MS:-500}
DC_CRITERION_HZ=${DC_CRITERION_HZ:-1.0}
DC_MIN_SPIKES=${DC_MIN_SPIKES:-2}
NO_FIGURES=${NO_FIGURES:-0}
OUTDIR="calibration_output"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export LANG=${LANG:-C.UTF-8}
export LC_ALL=${LC_ALL:-C.UTF-8}
export PYTHONIOENCODING=utf-8
export PYTHONUNBUFFERED=1
export HDF5_USE_FILE_LOCKING=FALSE

unset OMP_NUM_THREADS
export OMP_PROC_BIND=close
export OMP_PLACES=cores

echo "[Slurm] job=$SLURM_JOB_ID  ntasks=$SLURM_NTASKS  cpus-per-task=$SLURM_CPUS_PER_TASK"
echo "[Slurm] sim_ms=$SIM_MS  n_repeats=$N_REPEATS  rate_max=$RATE_MAX  rate_step=$RATE_STEP  weight=$WEIGHT"
echo "[Slurm] fine_rate_max=$FINE_RATE_MAX  fine_rate_step=$FINE_RATE_STEP  criterion_hz=$CRITERION_HZ"
echo "[Slurm] probe=$PROBE  dc_max=$DC_MAX  dc_step=$DC_STEP  dc_criterion_hz=$DC_CRITERION_HZ"

python3 - <<'PY'
import nest
ks = nest.GetKernelStatus()
thr = ks.get("local_num_threads", ks.get("num_threads", ks.get("threads", 1)))
print(f"nest {nest.__version__}  local_threads={thr}")
PY

mkdir -p "$OUTDIR"
OUTFILE="${OUTDIR}/dg_ca3_fi_calib.h5"
echo "[Slurm] output -> $OUTFILE"

OPTIONAL_FLAGS=""
[ "$NO_FIGURES" = "1" ] && OPTIONAL_FLAGS="$OPTIONAL_FLAGS --no-figures"

srun --cpu-bind=cores \
  python3 -u "calibration/nest_dg_ca3_fi_calibration.py" \
    --threads      "$SLURM_CPUS_PER_TASK" \
    --sim-ms       "$SIM_MS" \
    --n-repeats    "$N_REPEATS" \
    --rate-max       "$RATE_MAX" \
    --rate-step      "$RATE_STEP" \
    --fine-rate-max  "$FINE_RATE_MAX" \
    --fine-rate-step "$FINE_RATE_STEP" \
    --weight       "$WEIGHT" \
    --criterion-hz "$CRITERION_HZ" \
    --probe           "$PROBE" \
    --dc-max          "$DC_MAX" \
    --dc-step         "$DC_STEP" \
    --dc-sim-ms       "$DC_SIM_MS" \
    --dc-settle-ms    "$DC_SETTLE_MS" \
    --dc-criterion-hz "$DC_CRITERION_HZ" \
    --dc-min-spikes   "$DC_MIN_SPIKES" \
    --out-hdf5     "$OUTFILE" \
    $OPTIONAL_FLAGS
