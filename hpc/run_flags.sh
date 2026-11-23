#!/bin/bash -l
#SBATCH --job-name=HIPPO_FLAGS
#SBATCH --output=Nest_flags_%j.slurmout
#SBATCH --error=Nest_flags_%j.slurmerr
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=50
#SBATCH --time=20:00:00
#SBATCH --partition=gp_bsccs

# Fork launcher: runs replay_scaled.py with a flag file from hpc/flags/ (the exact flags of a
# 1% WORKLOG run), at SCALE with all SLURM cores. hpc/run.sh is unchanged; it has no pass-through
# for the fork's opt-in flags. Later flags override earlier ones (argparse), so --scale,
# --threads and --seed here replace the values in the file.
#
# Needs out/nous/mem3.json on the cluster (the flag files use --ec-memories; it is not in git).
#
# WORKLOG §44 relay config m1:
#  sbatch --export=ALL,FLAGS=hpc/flags/m1.flags,NAME=m1,SEED=202 hpc/run_flags.sh
# WORKLOG §48 consolidation, learning arm and no-plasticity twin (same seed):
#  sbatch --export=ALL,FLAGS=hpc/flags/L48.flags,NAME=L48,SEED=202 hpc/run_flags.sh
#  sbatch --export=ALL,FLAGS=hpc/flags/L48.flags,NAME=N48,SEED=202,EXTRA="--no-stc-hook --no-mpfc-assoc" hpc/run_flags.sh
# Score (from the repo root):
#  python analysis/score_chain.py results/m1_12pct_s202.h5
#  python analysis/score_cons.py results/L48_12pct_s202.h5 results/N48_12pct_s202.h5

set -euo pipefail
: "${FLAGS:?set FLAGS=hpc/flags/<name>.flags}"
: "${NAME:?set NAME}"
: "${SEED:?set SEED}"
SCALE=${SCALE:-12}
EXTRA=${EXTRA:-}
OUTDIR="results"
OUTFILE="${OUTDIR}/${NAME}_${SCALE}pct_s${SEED}.h5"

export LANG=${LANG:-C.UTF-8}
export LC_ALL=${LC_ALL:-C.UTF-8}
export PYTHONIOENCODING=utf-8
export PYTHONUNBUFFERED=1
export HDF5_USE_FILE_LOCKING=FALSE
unset OMP_NUM_THREADS
export OMP_PROC_BIND=close
export OMP_PLACES=cores

grep -q -- "--ec-memories" "$FLAGS" && [ ! -f out/nous/mem3.json ] && { echo "missing out/nous/mem3.json"; exit 1; }
mkdir -p "$OUTDIR"
echo "[Slurm] job=${SLURM_JOB_ID:-none} cpus=${SLURM_CPUS_PER_TASK:-?} flags=$FLAGS seed=$SEED scale=$SCALE extra=$EXTRA"
echo "[Slurm] git $(git rev-parse --short HEAD 2>/dev/null || echo '?') -> $OUTFILE"
# shellcheck disable=SC2046
srun --cpu-bind=cores \
  python3 -u replay_scaled.py $(cat "$FLAGS") $EXTRA \
    --scale "$SCALE" --threads "$SLURM_CPUS_PER_TASK" --seed "$SEED" \
    --out-hdf5 "$OUTFILE" --no-figures
